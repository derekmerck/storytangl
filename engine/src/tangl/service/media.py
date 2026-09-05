from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from tangl.core import Selector
from tangl.journal.fragments import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaInventory
from tangl.media.media_resource import MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.type_hints import Identifier

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


def resolve_world_media(
    *,
    world: Any,
    media: MediaRIT | Identifier,
    **kwargs: Any,
) -> MediaDataType:
    """Resolve one world media payload through the world's media registry."""

    if isinstance(media, MediaRIT):
        return media.get_content(**kwargs)

    media_registry = getattr(world, "media_registry", None)
    if media_registry is None or not hasattr(media_registry, "find_one"):
        raise ValueError(f"World '{world.label}' does not expose media resources")

    media_obj = media_registry.find_one(Selector(alias=media))
    if media_obj is None:
        raise ValueError(f"Media '{media}' not found for world '{world.label}'")
    return media_obj.get_content(**kwargs)


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
    """Return the served prefix for a scope.

    Branches on scope only. Routing some data types to a CMS while others stay on
    the media server would extend this to ``(scope, data_type) -> resolver`` --
    and belongs here, in server configuration, rather than on
    :class:`MediaRenderProfile`. The profile is per-request *client* policy; where
    the bytes live is per-deployment. One knob for both would let a client reroute
    storage. See ``MEDIA_DESIGN.md``.
    """

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
            found = registry.find_one(Selector(**criteria))
            if isinstance(found, MediaRIT):
                return found, inventory.scope
    return None


def _base_payload(
    fragment: MediaFragment,
    *,
    scope: str,
    media_type: MediaDataType | str | None,
    content_format: str | None,
    rit_id: UUID | None,
) -> dict[str, Any]:
    """Assemble the common media DTO fields.

    ``content_format`` is required rather than defaulted off the fragment
    because it describes **this payload**, not the fragment it came from. A
    dereferenced RIT is a URL, or bytes, or a path -- never still a ``"rit"``.
    Defaulting it made "forgot to relabel" the silent fallback, and a payload
    labelled ``"rit"`` promises clients an affordance it does not carry: no
    ``rit_id`` to resolve, and no endpoint to resolve it at.

    ``rit_id`` is required for the same reason, and names the resource this
    payload actually represents -- which is not always the fragment's own. A
    pending resource served through a static fallback carries the fallback's
    bytes, so reading identity off the fragment would describe one asset with
    another's id. It is provenance for the representation, useful now and the
    handle a RIT-aware client tier would key on later; see ``MEDIA_DESIGN.md``.
    """

    source_id = getattr(fragment, "source_id", None)
    payload = {
        "uid": str(fragment.uid),
        "fragment_type": "media",
        "media_role": getattr(fragment, "media_role", None),
        "text": getattr(fragment, "text", None),
        "source_id": str(source_id) if source_id is not None else None,
        "scope": scope,
        "media_type": (
            media_type.value if isinstance(media_type, MediaDataType) else media_type
        ),
        "content_format": content_format,
    }
    if rit_id is not None:
        payload["rit_id"] = str(rit_id)
    return payload


def _inline_data_payload(
    *,
    fragment: MediaFragment,
    scope: str,
    result: ResolvedMediaResult,
    rit_id: UUID | None,
) -> dict[str, Any]:
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
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=data_type,
                content_format="xml",
                rit_id=rit_id,
            ),
            "data": data,
        }

    base_payload = _base_payload(
        fragment,
        scope=scope,
        media_type=data_type,
        content_format="data",
        rit_id=rit_id,
    )
    if isinstance(data, bytes):
        return {**base_payload, "data": b64encode(data).decode("ascii")}
    return {**base_payload, "data": data}


def _passthrough_payload(
    *,
    fragment: MediaFragment,
    scope: str,
    result: ResolvedMediaResult,
    rit_id: UUID | None,
) -> dict[str, Any]:
    if result.url:
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=result.data_type,
                content_format="url",
                rit_id=rit_id,
            ),
            "url": result.url,
        }
    if result.path is not None:
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=result.data_type,
                content_format="path",
                rit_id=rit_id,
            ),
            "path": str(result.path),
        }
    return _inline_data_payload(
        fragment=fragment, scope=scope, result=result, rit_id=rit_id
    )


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
    content_type = result.data_type

    if result.url:
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=content_type,
                content_format="url",
                rit_id=rit.uid,
            ),
            "url": result.url,
        }

    if content_type in _UNSUPPORTED_MEDIA_TYPES:
        # Nothing is carried, so nothing is declared. A format naming a source
        # this payload does not have would be the same lie in a smaller hat.
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=content_type,
                content_format=None,
                rit_id=rit.uid,
            ),
            "unsupported_reason": "unsupported_media_type",
        }

    prefix = _url_prefix(scope=scope, world_id=world_id, story_id=story_id)
    media_root = _media_root_for_scope(
        scope=scope,
        world_media_root=world_media_root,
        story_media_root=story_media_root,
        system_media_root=system_media_root,
    )
    if prefix is not None and result.path is not None:
        return {
            **_base_payload(
                fragment,
                scope=scope,
                media_type=content_type,
                content_format="url",
                rit_id=rit.uid,
            ),
            "url": f"{prefix}/{_relative_url_path_for_rit(rit, media_root=media_root)}",
        }
    return _inline_data_payload(
        fragment=fragment, scope=scope, result=result, rit_id=rit.uid
    )


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
    # ``rit`` is the resource this payload represents, which on a static
    # fallback is not the fragment's own. Identity follows the bytes.
    if profile.content_profile == MediaContentProfile.INLINE_DATA:
        return _inline_data_payload(
            fragment=fragment, scope=scope, result=result, rit_id=rit.uid
        )
    if profile.content_profile == MediaContentProfile.PASSTHROUGH:
        return _passthrough_payload(
            fragment=fragment, scope=scope, result=result, rit_id=rit.uid
        )
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
    render_profile: MediaRenderProfile | None = None,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any] | None:
    """Flatten canonical media fragments into service-facing payloads."""

    if isinstance(fragment, MediaFragment):
        scope = getattr(fragment, "scope", None) or "world"
        payload_profile = render_profile or MediaRenderProfile()

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

        # Nothing was dereferenced on this path, so the fragment's own format
        # is this payload's format -- stated rather than defaulted.
        payload = _base_payload(
            fragment,
            scope=scope,
            media_type=getattr(fragment.content_type, "value", fragment.content_type),
            content_format=fragment.content_format,
            rit_id=fragment.rit_id,
        )

        if fragment.content_format == "url":
            payload["url"] = str(fragment.content)
            return payload

        if fragment.content_format == "data":
            content = fragment.content
            if isinstance(content, bytes):
                payload["data"] = b64encode(content).decode("ascii")
            else:
                payload["data"] = content
            return payload

        if fragment.content_format == "json" and isinstance(fragment.content, dict):
            return {**fragment.content, **payload}

        payload["content"] = fragment.content
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
