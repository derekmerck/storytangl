from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from typing import Any

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

_UNSUPPORTED_MEDIA_TYPES = {
    MediaDataType.AUDIO,
    MediaDataType.SFX,
    MediaDataType.VOICE,
    MediaDataType.MUSIC,
    MediaDataType.VIDEO,
    MediaDataType.ANIMATION,
}


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


def _resolved_rit_payload(
    rit: MediaRIT,
    *,
    payload: dict[str, Any],
    scope: str,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any]:
    content_type = getattr(rit, "data_type", None)
    payload["media_type"] = content_type.value if content_type is not None else None
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
    if prefix is not None:
        payload["url"] = f"{prefix}/{_relative_url_path_for_rit(rit, media_root=media_root)}"
    return payload


def media_fragment_to_payload(
    fragment: Any,
    *,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict[str, Any] | None:
    """Flatten canonical media fragments into service-facing payloads."""

    if isinstance(fragment, MediaFragment):
        scope = getattr(fragment, "scope", None) or "world"
        source_id = getattr(fragment, "source_id", None)
        payload: dict[str, Any] = {
            "fragment_type": "media",
            "media_role": getattr(fragment, "media_role", None),
            "text": getattr(fragment, "text", None),
            "source_id": str(source_id) if source_id is not None else None,
            "scope": scope,
            "content_format": fragment.content_format,
        }

        if fragment.content_format == "rit":
            rit = fragment.content
            if not isinstance(rit, MediaRIT):
                raise TypeError(f"Expected MediaRIT in MediaFragment.content, got {type(rit)}")
            return _resolved_rit_payload(
                rit,
                payload=payload,
                scope=scope,
                world_id=world_id,
                story_id=story_id,
                world_media_root=world_media_root,
                story_media_root=story_media_root,
                system_media_root=system_media_root,
            )

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
