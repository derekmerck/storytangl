from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator, get_user_locks
from tangl.rest.dependencies38 import (
    get_service_adapter38,
    get_user_locks38,
    resolve_user_auth38,
)
from tangl.service import Orchestrator
from tangl.service.exceptions import AccessDeniedError
from tangl.service38 import GatewayRestAdapter38, ServiceOperation38, UserAuthInfo
from tangl.service38.response import RuntimeInfo
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret


class ChoiceRequest(BaseModel):
    """Request payload for resolving a player choice."""

    choice_id: UUID | None = None
    uid: UUID | None = None
    payload: Any = None

    def resolve_choice_id(self) -> UUID:
        if self.choice_id is not None:
            return self.choice_id
        if self.uid is not None:
            return self.uid
        raise ValueError("choice_id or uid must be provided")


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


def _call_service38(
    adapter: GatewayRestAdapter38,
    operation: ServiceOperation38,
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


def _call_legacy(
    orchestrator: Orchestrator,
    endpoint_name: str,
    /,
    *,
    user_id: UUID | None = None,
    **params: Any,
) -> Any:
    kwargs = dict(params)
    if user_id is not None:
        kwargs["user_id"] = user_id
    try:
        return orchestrator.execute(endpoint_name, **kwargs)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _apply_legacy_render_profile(
    adapter: GatewayRestAdapter38,
    endpoint_name: str,
    payload: Any,
    *,
    render_profile: str,
    user_id: UUID | None,
) -> Any:
    """Apply service38 outbound rendering hooks to legacy payloads."""

    if render_profile.strip().lower() == "raw":
        return payload

    return adapter.gateway.hooks.run_outbound(
        payload,
        operation=f"endpoint:{endpoint_name}",
        render_profile=render_profile,
        user_id=user_id,
    )


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


def _extract_story38_envelope(result: RuntimeInfo) -> dict[str, Any]:
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
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Create a new story instance for the authenticated user (legacy path)."""
    _ = render_profile  # retained for API compatibility; legacy orchestrator is transport-agnostic
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    result = _call_legacy(
        orchestrator,
        "RuntimeController.create_story",
        user_id=user_auth.user_id,
        **kwargs,
    )
    details = getattr(result, "details", None) or {}
    ledger = details.get("ledger") if isinstance(details, dict) else None
    if ledger is not None and getattr(orchestrator, "persistence", None) is not None:
        orchestrator.persistence.save(ledger)

    if hasattr(result, "status") and hasattr(result, "details"):
        return _runtime_info_payload(result, flatten_details=True)
    return _serialize(result)


@router.get("/update")
async def get_story_update(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
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
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    fragments = _call_legacy(
        orchestrator,
        "RuntimeController.get_journal_entries",
        user_id=user_auth.user_id,
        limit=limit,
        marker=marker,
        start_marker=start_marker,
        end_marker=end_marker,
    )
    serialized_fragments = _serialize(fragments)
    serialized_fragments = _apply_legacy_render_profile(
        adapter,
        "RuntimeController.get_journal_entries",
        serialized_fragments,
        render_profile=render_profile,
        user_id=user_auth.user_id,
    )
    return {
        "fragments": serialized_fragments,
        "choices": _extract_choices_from_fragments(serialized_fragments),
    }


@router.post("/do")
async def do_story_action(
    request: ChoiceRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Resolve a player choice and return resulting legacy journal fragments."""
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_auth.user_id]:
        status = _call_legacy(
            orchestrator,
            "RuntimeController.resolve_choice",
            user_id=user_auth.user_id,
            choice_id=choice_id,
            choice_payload=request.payload,
        )
        fragments = _call_legacy(
            orchestrator,
            "RuntimeController.get_journal_entries",
            user_id=user_auth.user_id,
            limit=0,
        )

    payload = _serialize(status)
    if not isinstance(payload, dict):
        payload = {"status": payload}
    serialized_fragments = _serialize(fragments)
    payload["fragments"] = _apply_legacy_render_profile(
        adapter,
        "RuntimeController.get_journal_entries",
        serialized_fragments,
        render_profile=render_profile,
        user_id=user_auth.user_id,
    )
    return payload


@router.post("/story38/create")
async def create_story38(
    world_id: str = Query(..., description="World template to instantiate"),
    story_label: str | None = Query(None, description="Optional story label"),
    init_mode: str | None = Query(
        None,
        description="Initialization mode: LAZY or EAGER",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: str = Header(..., alias="X-API-Key"),
) -> dict[str, Any]:
    """Create a vm38/story38 session and return the initial envelope."""
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    if init_mode:
        kwargs["init_mode"] = init_mode

    result = _call_service38(
        adapter,
        ServiceOperation38.STORY38_CREATE,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
        **kwargs,
    )
    if not isinstance(result, RuntimeInfo):
        return _serialize(result)

    envelope = _extract_story38_envelope(result)
    payload = _runtime_info_payload(result, flatten_details=True)
    payload["envelope"] = envelope
    return payload


@router.get("/story38/update")
async def get_story_update38(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
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
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    result = _call_service38(
        adapter,
        ServiceOperation38.STORY38_UPDATE,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
        limit=limit,
        **({"since_step": since_step} if since_step is not None else {}),
    )

    if not isinstance(result, RuntimeInfo):
        return _serialize(result)
    return _extract_story38_envelope(result)


@router.post("/story38/do")
async def do_story_action38(
    request: ChoiceRequest = Body(...),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks38),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """Resolve a choice and return the vm38 envelope."""
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_auth.user_id]:
        result = _call_service38(
            adapter,
            ServiceOperation38.STORY38_DO,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            render_profile=render_profile,
            choice_id=choice_id,
            choice_payload=request.payload,
        )

    if not isinstance(result, RuntimeInfo):
        return _serialize(result)
    return _extract_story38_envelope(result)


@router.get("/story38/status")
async def get_story_status38(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """Return vm38 runtime status details."""
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    result = _call_service38(
        adapter,
        ServiceOperation38.STORY38_STATUS,
        user_id=user_auth.user_id,
        user_auth=user_auth,
        render_profile=render_profile,
    )
    if isinstance(result, RuntimeInfo):
        return _runtime_info_payload(result, flatten_details=True)
    return _serialize(result)


@router.get("/status")
async def get_story_status(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Return a lightweight summary of the current story state (legacy path)."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    return _serialize(
        _call_legacy(
            orchestrator,
            "RuntimeController.get_story_info",
            user_id=user_auth.user_id,
        )
    )


@router.delete("/drop")
async def reset_story(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """End the user's active story and optionally archive the ledger (legacy path)."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)

    try:
        async with user_locks[user_auth.user_id]:
            result = _call_legacy(
                orchestrator,
                "RuntimeController.drop_story",
                user_id=user_auth.user_id,
                archive=archive,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="python", exclude_none=True)
        if isinstance(payload.get("details"), dict):
            details_payload = payload.pop("details")
            payload.update(details_payload)
        if payload.get("message") == "Story dropped":
            payload["status"] = "dropped"
        return _serialize(payload)

    return _serialize(result)


@router.delete("/story38/drop")
async def reset_story38(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks38),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict[str, Any]:
    """End the active vm38 story and optionally archive the ledger."""
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    try:
        async with user_locks[user_auth.user_id]:
            result = _call_service38(
                adapter,
                ServiceOperation38.STORY38_DROP,
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
