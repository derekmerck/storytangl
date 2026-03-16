from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaInventory
from tangl.media.media_resource import MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

_UNSUPPORTED_MEDIA_TYPES = {
    MediaDataType.AUDIO,
    MediaDataType.SFX,
    MediaDataType.VOICE,
    MediaDataType.MUSIC,
    MediaDataType.VIDEO,
    MediaDataType.ANIMATION,
}


class MediaPendingPolicy(str, Enum):
    """Fallback policy for unresolved generated media."""

    DISCARD = "discard"
    POLL = "poll"
    FALLBACK = "fallback"


class MediaContentProfile(str, Enum):
    """Transport representation for resolved media."""

    INLINE_DATA = "inline_data"
    MEDIA_SERVER = "media_server"
    PASSTHROUGH = "passthrough"


@dataclass(frozen=True)
class MediaRenderProfile:
    """Internal service-layer media rendering policy."""

    pending_policy: MediaPendingPolicy = MediaPendingPolicy.FALLBACK
    content_profile: MediaContentProfile = MediaContentProfile.MEDIA_SERVER
    static_inventories: tuple[MediaInventory, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PendingMediaResult:
    job_id: str | None
    status: MediaRITStatus


@dataclass(frozen=True)
class ResolvedMediaResult:
    path: Path | None = None
    data: bytes | str | None = None
    data_type: MediaDataType | None = None
    url: str | None = None


@dataclass(frozen=True)
class FailedMediaResult:
    reason: str | None = None
    derivation_spec: dict[str, Any] | None = None


def _normalize_profile_tokens(render_profile: str | Iterable[str] | None) -> set[str]:
    if render_profile is None:
        return set()
    if isinstance(render_profile, str):
        return {
            token.strip().lower()
            for raw in render_profile.replace("+", ",").split(",")
            if (token := raw.strip())
        }
    return {str(token).strip().lower() for token in render_profile if str(token).strip()}


def _coerce_render_profile(render_profile: str | Iterable[str] | MediaRenderProfile | None) -> MediaRenderProfile:
    if isinstance(render_profile, MediaRenderProfile):
        return render_profile

    tokens = _normalize_profile_tokens(render_profile)
    content_profile = MediaContentProfile.MEDIA_SERVER
    if "inline_data" in tokens:
        content_profile = MediaContentProfile.INLINE_DATA
    elif "passthrough" in tokens:
        content_profile = MediaContentProfile.PASSTHROUGH
    elif "media_url" in tokens or "raw" in tokens:
        content_profile = MediaContentProfile.MEDIA_SERVER

    pending_policy = MediaPendingPolicy.FALLBACK
    if "poll_media" in tokens or "poll" in tokens:
        pending_policy = MediaPendingPolicy.POLL
    elif "discard_pending" in tokens:
        pending_policy = MediaPendingPolicy.DISCARD

    return MediaRenderProfile(
        pending_policy=pending_policy,
        content_profile=content_profile,
    )


def _relative_url_path_for_rit(
    rit: MediaRIT,
    *,
    media_root: Path | None = None,
) -> str:
    path_value = getattr(rit, "path", None)
    if isinstance(path_value, Path):
        if media_root is not None:
            try:
                relative_path = path_value.resolve().relative_to(media_root.resolve())
                return relative_path.as_posix()
            except (OSError, ValueError):
                pass
        if not path_value.is_absolute() and ".." not in path_value.parts:
            return path_value.as_posix()
        return path_value.name
    label = getattr(rit, "label", None)
    if isinstance(label, str) and label:
        return label
    raise ValueError(f"Cannot determine filename for MediaRIT {rit!r}")


def _url_prefix(*, scope: str, world_id: str | None, story_id: str | None) -> str | None:
    if scope == "sys":
        return "/media/sys"
    if scope == "story":
        if story_id is None:
            return None
        return f"/media/story/{story_id}"
    if world_id is None:
        return None
    return f"/media/world/{world_id}"


def _media_root_for_scope(
    *,
    scope: str,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> Path | None:
    if scope == "sys":
        return system_media_root
    if scope == "story":
        return story_media_root
    return world_media_root


def _resolve_media_data(rit: MediaRIT) -> PendingMediaResult | ResolvedMediaResult | FailedMediaResult:
    status = getattr(rit, "status", MediaRITStatus.RESOLVED)
    if status in {MediaRITStatus.PENDING, MediaRITStatus.RUNNING}:
        return PendingMediaResult(
            job_id=getattr(rit, "job_id", None),
            status=status,
        )
    if status == MediaRITStatus.FAILED:
        return FailedMediaResult(
            reason="generation_failed",
            derivation_spec=getattr(rit, "derivation_spec", None),
        )

    path = getattr(rit, "path", None)
    if isinstance(path, Path) and path.is_file():
        return ResolvedMediaResult(path=path, data_type=getattr(rit, "data_type", None))

    data = getattr(rit, "data", None)
    if data is not None:
        return ResolvedMediaResult(data=data, data_type=getattr(rit, "data_type", None))

    return FailedMediaResult(
        reason="missing_media_source",
        derivation_spec=getattr(rit, "derivation_spec", None),
    )


def _content_payload_from_text(fragment: MediaFragment, text: str) -> dict[str, Any]:
    source_id = getattr(fragment, "source_id", None)
    return {
        "fragment_type": "content",
        "content": text,
        "text": text,
        "source_id": str(source_id) if source_id is not None else None,
    }


def _fallback_text(fragment: MediaFragment) -> str | None:
    for attr in ("fallback_text", "text"):
        value = getattr(fragment, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _fallback_ref_from_rit(rit: MediaRIT) -> str | None:
    for payload in (
        getattr(rit, "derivation_spec", None),
        getattr(rit, "adapted_spec", None),
    ):
        if isinstance(payload, dict):
            fallback_ref = payload.get("fallback_ref")
            if isinstance(fallback_ref, str) and fallback_ref.strip():
                return fallback_ref.strip()
    return None


def _resolve_fallback_rit(
    rit: MediaRIT,
    inventories: Iterable[MediaInventory],
) -> tuple[MediaRIT, str] | None:
    fallback_ref = _fallback_ref_from_rit(rit)
    if not fallback_ref:
        return None

    fallback_path = Path(fallback_ref)
    fallback_name = fallback_path.name
    for inventory in inventories:
        registry = inventory.registry
        for criteria in (
            {"has_identifier": fallback_ref},
            {"path": fallback_path},
            {"label": fallback_name},
        ):
            found = registry.find_one(**criteria)
            if isinstance(found, MediaRIT):
                return found, inventory.scope
    return None


def _base_payload(fragment: MediaFragment, *, scope: str, media_type: MediaDataType | None) -> dict[str, Any]:
    source_id = getattr(fragment, "source_id", None)
    return {
        "fragment_type": "media",
        "media_role": getattr(fragment, "media_role", None),
        "text": getattr(fragment, "text", None),
        "source_id": str(source_id) if source_id is not None else None,
        "scope": scope,
        "media_type": media_type.value if media_type is not None else None,
        "content_format": getattr(fragment, "content_format", None),
    }


def _inline_data_payload(
    *,
    fragment: MediaFragment,
    scope: str,
    result: ResolvedMediaResult,
) -> dict[str, Any]:
    base_payload = _base_payload(fragment, scope=scope, media_type=result.data_type)
    data = result.data
    data_type = result.data_type

    if data is None and result.path is not None:
        if data_type == MediaDataType.VECTOR:
            data = result.path.read_text(encoding="utf-8")
        else:
            data = result.path.read_bytes()

    if data_type == MediaDataType.VECTOR:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return {**base_payload, "content_format": "xml", "data": data}

    if isinstance(data, bytes):
        return {
            **base_payload,
            "content_format": "data",
            "data": b64encode(data).decode("ascii"),
        }
    return {
        **base_payload,
        "content_format": "data",
        "data": data,
    }


def _passthrough_payload(
    *,
    fragment: MediaFragment,
    scope: str,
    result: ResolvedMediaResult,
) -> dict[str, Any]:
    base_payload = _base_payload(fragment, scope=scope, media_type=result.data_type)
    if result.url:
        return {**base_payload, "content_format": "url", "url": result.url}
    if result.path is not None:
        return {**base_payload, "content_format": "path", "path": str(result.path)}
    return _inline_data_payload(fragment=fragment, scope=scope, result=result)


def _media_server_payload(
    *,
    fragment: MediaFragment,
    rit: MediaRIT,
    scope: str,
    result: ResolvedMediaResult,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any]:
    if result.url:
        return {
            **_base_payload(fragment, scope=scope, media_type=result.data_type),
            "url": result.url,
        }

    content_type = result.data_type
    payload = _base_payload(fragment, scope=scope, media_type=content_type)
    if content_type in _UNSUPPORTED_MEDIA_TYPES:
        payload["unsupported_reason"] = "unsupported_media_type"
        return payload

    prefix = _url_prefix(scope=scope, world_id=world_id, story_id=story_id)
    media_root = _media_root_for_scope(
        scope=scope,
        world_media_root=world_media_root,
        story_media_root=story_media_root,
        system_media_root=system_media_root,
    )
    if prefix is not None and result.path is not None:
        payload["url"] = f"{prefix}/{_relative_url_path_for_rit(rit, media_root=media_root)}"
        return payload
    return _inline_data_payload(fragment=fragment, scope=scope, result=result)


def _resolved_rit_payload(
    rit: MediaRIT,
    *,
    fragment: MediaFragment,
    scope: str,
    result: ResolvedMediaResult,
    profile: MediaRenderProfile,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any]:
    if profile.content_profile == MediaContentProfile.INLINE_DATA:
        return _inline_data_payload(fragment=fragment, scope=scope, result=result)
    if profile.content_profile == MediaContentProfile.PASSTHROUGH:
        return _passthrough_payload(fragment=fragment, scope=scope, result=result)
    return _media_server_payload(
        fragment=fragment,
        rit=rit,
        scope=scope,
        result=result,
        world_id=world_id,
        story_id=story_id,
        world_media_root=world_media_root,
        story_media_root=story_media_root,
        system_media_root=system_media_root,
    )


def _pending_or_failed_payload(
    *,
    fragment: MediaFragment,
    rit: MediaRIT,
    result: PendingMediaResult | FailedMediaResult,
    profile: MediaRenderProfile,
    scope: str,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any] | None:
    if profile.pending_policy == MediaPendingPolicy.POLL and isinstance(result, PendingMediaResult):
        source_id = getattr(fragment, "source_id", None)
        return {
            "fragment_type": "control",
            "directive": "poll_media",
            "job_id": result.job_id,
            "media_role": getattr(fragment, "media_role", None),
            "retry_after_ms": 2000,
            "source_id": str(source_id) if source_id is not None else None,
        }

    if profile.pending_policy == MediaPendingPolicy.DISCARD:
        return None

    fallback = _resolve_fallback_rit(rit, profile.static_inventories)
    if fallback is not None:
        fallback_rit, fallback_scope = fallback
        fallback_result = _resolve_media_data(fallback_rit)
        if isinstance(fallback_result, ResolvedMediaResult):
            return _resolved_rit_payload(
                fallback_rit,
                fragment=fragment,
                scope=fallback_scope,
                result=fallback_result,
                profile=profile,
                world_id=world_id,
                story_id=story_id,
                world_media_root=world_media_root,
                story_media_root=story_media_root,
                system_media_root=system_media_root,
            )

    fallback_text = _fallback_text(fragment)
    if fallback_text is not None:
        return _content_payload_from_text(fragment, fallback_text)
    return None


def media_fragment_to_payload(
    fragment: Any,
    *,
    render_profile: str | Iterable[str] | MediaRenderProfile | None = None,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any] | None:
    """Flatten canonical media fragments into service-facing payloads."""

    if isinstance(fragment, MediaFragment):
        scope = getattr(fragment, "scope", None) or "world"
        payload_profile = _coerce_render_profile(render_profile)

        if fragment.content_format == "rit":
            rit = fragment.content
            if not isinstance(rit, MediaRIT):
                raise TypeError(f"Expected MediaRIT in MediaFragment.content, got {type(rit)}")

            result = _resolve_media_data(rit)
            if isinstance(result, ResolvedMediaResult):
                return _resolved_rit_payload(
                    rit,
                    fragment=fragment,
                    scope=scope,
                    result=result,
                    profile=payload_profile,
                    world_id=world_id,
                    story_id=story_id,
                    world_media_root=world_media_root,
                    story_media_root=story_media_root,
                    system_media_root=system_media_root,
                )
            return _pending_or_failed_payload(
                fragment=fragment,
                rit=rit,
                result=result,
                profile=payload_profile,
                scope=scope,
                world_id=world_id,
                story_id=story_id,
                world_media_root=world_media_root,
                story_media_root=story_media_root,
                system_media_root=system_media_root,
            )

        source_id = getattr(fragment, "source_id", None)
        payload: dict[str, Any] = {
            "fragment_type": "media",
            "media_role": getattr(fragment, "media_role", None),
            "text": getattr(fragment, "text", None),
            "source_id": str(source_id) if source_id is not None else None,
            "scope": scope,
            "content_format": fragment.content_format,
        }

        if fragment.content_format == "url":
            payload["url"] = str(fragment.content)
            payload["media_type"] = getattr(fragment.content_type, "value", fragment.content_type)
            return payload

        if fragment.content_format == "data":
            content = fragment.content
            if isinstance(content, bytes):
                payload["data"] = b64encode(content).decode("ascii")
            else:
                payload["data"] = content
            payload["media_type"] = getattr(fragment.content_type, "value", fragment.content_type)
            return payload

        if fragment.content_format == "json" and isinstance(fragment.content, dict):
            payload.update(fragment.content)
            payload["media_type"] = getattr(fragment.content_type, "value", fragment.content_type)
            return payload

        payload["content"] = fragment.content
        payload["media_type"] = getattr(fragment.content_type, "value", fragment.content_type)
        return payload

    if getattr(fragment, "fragment_type", None) == "media" and hasattr(fragment, "payload"):
        payload = getattr(fragment, "payload", None)
        if isinstance(payload, dict):
            result = {"fragment_type": "media", **payload}
            source_id = getattr(fragment, "source_id", None)
            if source_id is not None:
                result["source_id"] = str(source_id)
            return result

    return None
