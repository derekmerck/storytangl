from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict

from tangl.config import get_story_media_dir, get_sys_media_dir, settings
from tangl.journal.fragments import MediaFragment, fragment_to_dto
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    get_user_locks,
    require_service_access,
    resolve_user_auth,
)
from tangl.service import ServiceManager, UserAuthInfo
from tangl.service.exceptions import AccessDeniedError, AuthMismatchError
from tangl.service.media import (
    MediaContentProfile,
    MediaPendingPolicy,
    MediaRenderProfile,
    media_fragment_to_payload,
)
from tangl.service.response import JsonValue, RuntimeEnvelope, RuntimeInfo
from tangl.service.world_registry import resolve_world
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret


class ChoiceRequest(BaseModel):
    """Request payload for resolving a player choice."""

    edge_id: UUID
    payload: Any = None

    model_config = ConfigDict(extra="forbid")


router = APIRouter(tags=["Story"])
_MARKDOWN = MarkdownIt()


def _serialize(value: Any) -> Any:
    """Best-effort JSON-safe encoding for runtime payloads."""

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
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


def _normalize_profile_tokens(render_profile: str | Iterable[str] | None) -> set[str]:
    if render_profile is None:
        return {"raw"}
    if isinstance(render_profile, str):
        chunks = [part.strip().lower() for part in render_profile.replace("+", ",").split(",")]
        return {chunk for chunk in chunks if chunk} or {"raw"}
    return {str(token).strip().lower() for token in render_profile if str(token).strip()} or {"raw"}


def _profile_has(render_profile: str | Iterable[str] | None, token: str) -> bool:
    return token.lower() in _normalize_profile_tokens(render_profile)


def _parse_kinds(value: str | None) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_info_query(value: str | None) -> dict[str, JsonValue] | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=_bad_request_detail(exc),
        ) from exc
    if parsed is None:
        return None
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=400,
            detail="story-info query must be a JSON object",
        )
    return dict(parsed)


def _media_render_profile(render_profile: str | Iterable[str] | None) -> MediaRenderProfile:
    tokens = _normalize_profile_tokens(render_profile)

    content_profile = MediaContentProfile.MEDIA_SERVER
    if "inline_data" in tokens:
        content_profile = MediaContentProfile.INLINE_DATA
    elif "passthrough" in tokens:
        content_profile = MediaContentProfile.PASSTHROUGH

    pending_policy = MediaPendingPolicy.FALLBACK
    if "poll_media" in tokens or "poll" in tokens:
        pending_policy = MediaPendingPolicy.POLL
    elif "discard_pending" in tokens:
        pending_policy = MediaPendingPolicy.DISCARD

    return MediaRenderProfile(
        pending_policy=pending_policy,
        content_profile=content_profile,
    )


def _transform_text_fields(value: Any) -> Any:
    if isinstance(value, str):
        return _MARKDOWN.render(value)
    if isinstance(value, list):
        return [_transform_text_fields(item) for item in value]
    if isinstance(value, dict):
        transformed: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"text", "content"} and isinstance(item, str):
                transformed[key] = _MARKDOWN.render(item)
            else:
                transformed[key] = _transform_text_fields(item)
        return transformed
    return value


def _normalize_choice_labels_in_fragments(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure choice fragments expose ``label`` consistently."""

    def _normalize_choice_data(choice: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(choice)
        if normalized.get("source_label") and not normalized.get("label"):
            normalized["label"] = normalized["source_label"]
        if normalized.get("text") and not normalized.get("label"):
            normalized["label"] = normalized["text"]
        if normalized.get("content") and not normalized.get("label"):
            normalized["label"] = normalized["content"]
        return normalized

    normalized_fragments: list[dict[str, Any]] = []
    for fragment in fragments:
        normalized_fragment = dict(fragment)
        fragment_type = normalized_fragment.get("fragment_type")
        if fragment_type == "choice":
            normalized_fragment = _normalize_choice_data(normalized_fragment)
        elif fragment_type == "block":
            embedded = normalized_fragment.get("choices")
            if isinstance(embedded, list):
                normalized_fragment["choices"] = [
                    _normalize_choice_data(choice)
                    for choice in embedded
                    if isinstance(choice, dict)
                ]
        normalized_fragments.append(normalized_fragment)

    return normalized_fragments


def _resolve_world_media_root(world_id: str | None) -> Path | None:
    if world_id is None:
        return None
    try:
        world = resolve_world(world_id)
    except Exception:
        return None
    resource_path = getattr(getattr(world, "resources", None), "resource_path", None)
    return resource_path if isinstance(resource_path, Path) else None


def _serialize_fragment(
    fragment: Any,
    *,
    media_profile: MediaRenderProfile,
    world_id: str | None,
    story_id: str | None,
    world_media_root: Path | None,
    story_media_root: Path | None,
    system_media_root: Path | None,
) -> dict[str, Any] | None:
    media_payload = media_fragment_to_payload(
        fragment,
        render_profile=media_profile,
        world_id=world_id,
        story_id=story_id,
        world_media_root=world_media_root,
        story_media_root=story_media_root,
        system_media_root=system_media_root,
    )
    if media_payload is not None:
        return _serialize(media_payload)
    if isinstance(fragment, MediaFragment):
        return None
    if hasattr(fragment, "model_dump"):
        return _serialize(fragment_to_dto(fragment))
    if hasattr(fragment, "unstructure"):
        return _serialize(fragment.unstructure())
    return {"fragment_type": "unknown", "content": str(fragment)}


def _serialize_runtime_envelope(
    envelope: RuntimeEnvelope,
    *,
    render_profile: str = "raw",
) -> dict[str, Any]:
    profile_tokens = _normalize_profile_tokens(render_profile)
    media_profile = _media_render_profile(profile_tokens)
    envelope_payload = envelope.to_dto()
    metadata = dict(envelope_payload.get("metadata") or {})
    world_id = str(metadata["world_id"]) if metadata.get("world_id") is not None else None
    story_id = str(metadata["ledger_id"]) if metadata.get("ledger_id") is not None else None
    world_media_root = _resolve_world_media_root(world_id)
    story_media_root = get_story_media_dir(story_id) if story_id is not None else None
    system_media_root = get_sys_media_dir()

    fragments: list[dict[str, Any]] = []
    for fragment in envelope.fragments:
        payload = _serialize_fragment(
            fragment,
            media_profile=media_profile,
            world_id=world_id,
            story_id=story_id,
            world_media_root=world_media_root,
            story_media_root=story_media_root,
            system_media_root=system_media_root,
        )
        if payload is not None:
            fragments.append(payload)

    payload = {
        **envelope_payload,
        "fragments": _normalize_choice_labels_in_fragments(fragments),
    }
    serialized = _serialize(payload)
    if "html" in profile_tokens:
        serialized = _transform_text_fields(serialized)
    return serialized


def _runtime_info_payload(
    result: RuntimeInfo,
    *,
    flatten_details: bool = False,
) -> dict[str, Any]:
    """Serialize ``RuntimeInfo`` into a JSON-safe mapping."""

    details = dict(result.details or {})
    payload: dict[str, Any] = {
        "status": result.status,
        "code": result.code,
        "message": result.message,
        "cursor_id": result.cursor_id,
        "step": result.step,
    }
    payload = {key: value for key, value in payload.items() if value is not None}

    if details:
        serialized_details = _serialize(details)
        if flatten_details:
            payload.update(serialized_details)
        else:
            payload["details"] = serialized_details
    return _serialize(payload)


def _bad_request_detail(exc: ValueError) -> str:
    detail = str(exc)
    if detail == "User has no active ledger":
        return "No active story"
    return detail


def _call_service_method(
    service_manager: ServiceManager,
    method_name: str,
    *,
    auth_context: UserAuthInfo | None = None,
    **params: Any,
) -> Any:
    require_service_access(method_name, user_auth=auth_context)
    method = getattr(service_manager, method_name)
    try:
        return method(**params)
    except (AccessDeniedError, AuthMismatchError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/story/create")
async def create_story(
    world_id: str = Query(..., description="World template to instantiate"),
    story_label: str | None = Query(None, description="Optional story label"),
    init_mode: str | None = Query(
        None,
        description="Initialization mode: LAZY or EAGER",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    service_manager: ServiceManager = Depends(get_service_manager),
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Create a story session and return the initial runtime envelope."""

    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    if init_mode:
        kwargs["init_mode"] = init_mode

    try:
        envelope = _call_service_method(
            service_manager,
            "create_story",
            auth_context=user_auth,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            **kwargs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_bad_request_detail(exc)) from exc

    return _serialize_runtime_envelope(envelope, render_profile=render_profile)


@router.get("/update")
async def get_story_update(
    service_manager: ServiceManager = Depends(get_service_manager),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    limit: int = Query(default=0, ge=0),
    since_step: int | None = Query(
        None,
        description="Inclusive starting step; defaults to 0 (full history).",
    ),
) -> dict[str, Any]:
    """Return the runtime envelope with ordered fragments."""

    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    try:
        result = _call_service_method(
            service_manager,
            "get_story_update",
            auth_context=user_auth,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            limit=limit,
            **({"since_step": since_step} if since_step is not None else {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_bad_request_detail(exc)) from exc

    return _serialize_runtime_envelope(result, render_profile=render_profile)


@router.post("/do")
async def do_story_action(
    request: ChoiceRequest = Body(...),
    service_manager: ServiceManager = Depends(get_service_manager),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Resolve a player choice and return the updated runtime envelope."""

    user_auth = resolve_user_auth(api_key, service_manager=service_manager)

    try:
        async with user_locks[user_auth.user_id]:
            result = _call_service_method(
                service_manager,
                "resolve_choice",
                auth_context=user_auth,
                user_id=user_auth.user_id,
                user_auth=user_auth,
                edge_id=request.edge_id,
                choice_payload=request.payload,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_bad_request_detail(exc)) from exc

    return _serialize_runtime_envelope(result, render_profile=render_profile)


@router.get("/info")
async def get_story_info(
    service_manager: ServiceManager = Depends(get_service_manager),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    kind: str | None = Query(default=None, description="Projected-state channel kind."),
    kinds: str | None = Query(
        default=None,
        description="Comma-separated projected-state channel kinds.",
    ),
    query: str | None = Query(
        default=None,
        description="JSON-encoded opaque projected-state query descriptor.",
    ),
):
    """Return runtime status details for the active story."""

    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    parsed_query = _parse_info_query(query)
    try:
        result = _call_service_method(
            service_manager,
            "get_story_info",
            auth_context=user_auth,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            kind=kind,
            kinds=_parse_kinds(kinds),
            query=parsed_query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_bad_request_detail(exc)) from exc

    payload = result.to_dto() if hasattr(result, "to_dto") else _serialize(result)
    if _profile_has(render_profile, "html"):
        payload = _transform_text_fields(payload)
    return payload


@router.delete("/drop")
async def reset_story(
    service_manager: ServiceManager = Depends(get_service_manager),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """End the user's active story and optionally archive the ledger."""

    _ = render_profile
    user_auth = resolve_user_auth(api_key, service_manager=service_manager)

    try:
        async with user_locks[user_auth.user_id]:
            result = _call_service_method(
                service_manager,
                "drop_story",
                auth_context=user_auth,
                user_id=user_auth.user_id,
                user_auth=user_auth,
                archive=archive,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_bad_request_detail(exc)) from exc

    return _runtime_info_payload(result, flatten_details=True)
