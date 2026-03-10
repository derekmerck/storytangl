from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict

from tangl.config import settings
from tangl.rest.dependencies_gateway import (
    get_service_adapter,
    get_user_locks,
    resolve_user_auth,
)
from tangl.service.exceptions import AccessDeniedError
from tangl.service import GatewayRestAdapter, ServiceOperation, UserAuthInfo
from tangl.service.response import RuntimeInfo
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret


class ChoiceRequest(BaseModel):
    """Request payload for resolving a player choice."""

    choice_id: UUID | None = None
    payload: Any = None

    model_config = ConfigDict(extra="forbid")

    def resolve_choice_id(self) -> UUID:
        if self.choice_id is not None:
            return self.choice_id
        raise ValueError("choice_id must be provided")


router = APIRouter(tags=["Story"])


def _serialize(value: Any) -> Any:
    """Best-effort JSON encoding for fragments and response payloads."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, set):
        return [_serialize(item) for item in sorted(value, key=str)]
    if isinstance(value, type):
        return value.__name__
    if callable(value):
        return repr(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="python")
        return {key: _serialize(item) for key, item in data.items()}
    return value


def _extract_choices_from_fragments(fragments: list[Any]) -> list[dict[str, Any]]:
    """Extract choice fragments from a fragment stream for REST responses."""

    def _normalize(choice: Any) -> dict[str, Any]:
        normalized = choice if isinstance(choice, dict) else _serialize(choice)

        if not isinstance(normalized, dict):
            return {"value": normalized}

        result = dict(normalized)
        if "source_id" in result:
            result["uid"] = result["source_id"]
        elif "uid" in result:
            result["uid"] = result["uid"]
        if result.get("source_label") and not result.get("label"):
            result["label"] = result["source_label"]
        if result.get("text") and not result.get("label"):
            result["label"] = result["text"]
        if result.get("content") and not result.get("label"):
            result["label"] = result["content"]
        return result

    choices: list[dict[str, Any]] = []
    for fragment in fragments:
        fragment_data = fragment if isinstance(fragment, dict) else _serialize(fragment)
        fragment_type = fragment_data.get("fragment_type")
        embedded = fragment_data.get("choices")

        if fragment_type == "block":
            if embedded:
                choices.extend(_normalize(choice) for choice in embedded)
        elif fragment_type == "choice":
            choices.append(_normalize(fragment_data))

    return choices


def _normalize_choice_labels_in_fragments(fragments: list[Any]) -> list[Any]:
    """Ensure choice fragments expose ``label`` consistently."""

    def _normalize_choice_data(choice: Any) -> Any:
        if not isinstance(choice, dict):
            return choice
        normalized = dict(choice)
        if normalized.get("source_label") and not normalized.get("label"):
            normalized["label"] = normalized["source_label"]
        if normalized.get("text") and not normalized.get("label"):
            normalized["label"] = normalized["text"]
        if normalized.get("content") and not normalized.get("label"):
            normalized["label"] = normalized["content"]
        return normalized

    normalized_fragments: list[Any] = []
    for fragment in fragments:
        if not isinstance(fragment, dict):
            normalized_fragments.append(fragment)
            continue

        normalized_fragment = dict(fragment)
        fragment_type = normalized_fragment.get("fragment_type")
        if fragment_type == "choice":
            normalized_fragment = _normalize_choice_data(normalized_fragment)
        elif fragment_type == "block":
            embedded = normalized_fragment.get("choices")
            if isinstance(embedded, list):
                normalized_fragment["choices"] = [_normalize_choice_data(choice) for choice in embedded]

        normalized_fragments.append(normalized_fragment)

    return normalized_fragments


def _call_service(
    adapter: GatewayRestAdapter,
    operation: ServiceOperation,
    /,
    *,
    render_profile: str = "raw",
    user_id: UUID | None = None,
    user_auth: UserAuthInfo | None = None,
    **params: Any,
) -> Any:
    try:
        return adapter.execute_operation(
            operation,
            user_id=user_id,
            user_auth=user_auth,
            render_profile=render_profile,
            **params,
        )
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _call_endpoint(
    adapter: GatewayRestAdapter,
    endpoint_name: str,
    /,
    *,
    render_profile: str = "raw",
    user_id: UUID | None = None,
    user_auth: UserAuthInfo | None = None,
    **params: Any,
) -> Any:
    try:
        return adapter.gateway.execute_endpoint(
            endpoint_name,
            user_id=user_id,
            user_auth=user_auth,
            render_profile=render_profile,
            **params,
        )
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _runtime_info_payload(
    result: Any,
    *,
    flatten_details: bool = False,
) -> dict[str, Any]:
    """Serialize RuntimeInfo-like payloads into JSON-safe mappings."""
    details = dict(getattr(result, "details", None) or {})
    details.pop("ledger", None)

    payload: dict[str, Any] = {
        "status": getattr(result, "status", None),
        "code": getattr(result, "code", None),
        "message": getattr(result, "message", None),
        "cursor_id": getattr(result, "cursor_id", None),
        "step": getattr(result, "step", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    if details:
        if flatten_details:
            payload.update(details)
        else:
            payload["details"] = details

    return _serialize(payload)


def _extract_story_envelope(result: RuntimeInfo) -> dict[str, Any]:
    """Return the vm38 envelope payload from RuntimeInfo."""
    details = dict(result.details or {})
    details.pop("ledger", None)

    envelope = details.get("envelope")
    if not isinstance(envelope, dict):
        raise ValueError("Missing or invalid story38 envelope")
    return _serialize(envelope)


@router.post("/story/create")
async def create_story(
    world_id: str = Query(..., description="World template to instantiate"),
    story_label: str | None = Query(None, description="Optional story label"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Create a new story instance for the authenticated user."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    result = _call_endpoint(
        adapter,
        "RuntimeController.create_story",
        render_profile=render_profile,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        **kwargs,
    )
    details = getattr(result, "details", None) or {}
    ledger = details.get("ledger") if isinstance(details, dict) else None
    if ledger is not None and adapter.persistence is not None:
        adapter.persistence.save(ledger)

    if hasattr(result, "status") and hasattr(result, "details"):
        return _runtime_info_payload(result, flatten_details=True)
    return _serialize(result)


@router.get("/update")
async def get_story_update(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    limit: int = Query(default=0, ge=0),
    marker: str | None = Query(
        default=None,
        description="Return journal fragments for a specific journal marker/step.",
    ),
    start_marker: str | None = Query(
        default=None,
        description="Inclusive starting marker when requesting a range of steps.",
    ),
    end_marker: str | None = Query(
        default=None,
        description="Exclusive end marker for a marker range.",
    ),
) -> dict[str, Any]:
    """Return journal fragments for legacy story sessions."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    fragments = _call_endpoint(
        adapter,
        "RuntimeController.get_journal_entries",
        render_profile=render_profile,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        limit=limit,
        marker=marker,
        start_marker=start_marker,
        end_marker=end_marker,
    )
    serialized_fragments = _serialize(fragments)
    serialized_fragments = _normalize_choice_labels_in_fragments(serialized_fragments)
    return {
        "fragments": serialized_fragments,
        "choices": _extract_choices_from_fragments(serialized_fragments),
    }


@router.post("/do")
async def do_story_action(
    request: ChoiceRequest = Body(...),
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Resolve a player choice and return resulting legacy journal fragments."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_auth.user_id]:
        status = _call_endpoint(
            adapter,
            "RuntimeController.resolve_choice",
            render_profile=render_profile,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            choice_id=choice_id,
            choice_payload=request.payload,
        )
        fragments = _call_endpoint(
            adapter,
            "RuntimeController.get_journal_entries",
            render_profile=render_profile,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            limit=0,
        )

    payload = _serialize(status)
    if not isinstance(payload, dict):
        payload = {"status": payload}
    serialized_fragments = _serialize(fragments)
    serialized_fragments = _normalize_choice_labels_in_fragments(serialized_fragments)
    payload["fragments"] = serialized_fragments
    return payload


@router.post("/story38/create")
async def create_story_runtime(
    world_id: str = Query(..., description="World template to instantiate"),
    story_label: str | None = Query(None, description="Optional story label"),
    init_mode: str | None = Query(
        None,
        description="Initialization mode: LAZY or EAGER",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: str = Header(..., alias="X-API-Key"),
) -> dict[str, Any]:
    """Create a vm38/story38 session and return the initial envelope."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    if init_mode:
        kwargs["init_mode"] = init_mode

    result = _call_service(
        adapter,
        ServiceOperation.STORY38_CREATE,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
        **kwargs,
    )
    if not isinstance(result, RuntimeInfo):
        return _serialize(result)

    envelope = _extract_story_envelope(result)
    payload = _runtime_info_payload(result, flatten_details=True)
    payload["envelope"] = envelope
    return payload


@router.get("/story38/update")
async def get_story_update_runtime(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    since_step: int | None = Query(
        None,
        description="Inclusive starting step; defaults to 0 (full history).",
    ),
    limit: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return vm38 envelope with ordered fragments."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    result = _call_service(
        adapter,
        ServiceOperation.STORY38_UPDATE,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
        limit=limit,
        **({"since_step": since_step} if since_step is not None else {}),
    )

    if not isinstance(result, RuntimeInfo):
        return _serialize(result)
    return _extract_story_envelope(result)


@router.post("/story38/do")
async def do_story_action_runtime(
    request: ChoiceRequest = Body(...),
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """Resolve a choice and return the vm38 envelope."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_auth.user_id]:
        result = _call_service(
            adapter,
            ServiceOperation.STORY38_DO,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            render_profile=render_profile,
            choice_id=choice_id,
            choice_payload=request.payload,
        )

    if not isinstance(result, RuntimeInfo):
        return _serialize(result)
    return _extract_story_envelope(result)


@router.get("/story38/status")
async def get_story_status_runtime(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """Return vm38 runtime status details."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    result = _call_service(
        adapter,
        ServiceOperation.STORY38_STATUS,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
    )
    if isinstance(result, RuntimeInfo):
        return _runtime_info_payload(result, flatten_details=True)
    return _serialize(result)


@router.get("/info")
async def get_story_info(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Return a lightweight summary of the current story state (legacy path)."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    return _serialize(
        _call_endpoint(
            adapter,
            "RuntimeController.get_story_info",
            render_profile=render_profile,
            user_id=user_auth.user_id,
            user_auth=user_auth,
        )
    )


@router.get("/status")
async def get_story_status_alias(
    response: Response,
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Deprecated alias for :route:`GET /story/info`."""
    response.headers["Deprecation"] = "true"
    response.headers["Warning"] = '299 - "Deprecated endpoint: use /story/info"'
    response.headers["X-Deprecated-Endpoint"] = "/story/status"
    response.headers["X-Replacement-Endpoint"] = "/story/info"
    return await get_story_info(
        adapter=adapter,
        api_key=api_key,
        render_profile=render_profile,
    )


@router.delete("/drop")
async def reset_story(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """End the user's active story and optionally archive the ledger."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)

    try:
        async with user_locks[user_auth.user_id]:
            result = _call_endpoint(
                adapter,
                "RuntimeController.drop_story",
                render_profile=render_profile,
                user_id=user_auth.user_id,
                user_auth=user_auth,
                archive=archive,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="python", exclude_none=True)
        if isinstance(payload.get("details"), dict):
            details_payload = payload.pop("details")
            payload.update(details_payload)
        return _serialize(payload)

    return _serialize(result)


@router.delete("/story38/drop")
async def reset_story_runtime(
    adapter: GatewayRestAdapter = Depends(get_service_adapter),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """End the active vm38 story and optionally archive the ledger."""
    user_auth = resolve_user_auth(api_key, adapter=adapter)
    try:
        async with user_locks[user_auth.user_id]:
            result = _call_service(
                adapter,
                ServiceOperation.STORY38_DROP,
                user_id=user_auth.user_id,
                user_auth=user_auth,
                render_profile=render_profile,
                archive=archive,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(result, RuntimeInfo):
        return _runtime_info_payload(result, flatten_details=True)
    return _serialize(result)
