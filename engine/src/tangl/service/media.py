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


def _filename_for_rit(rit: MediaRIT) -> str:
    path_value = getattr(rit, "path", None)
    if isinstance(path_value, Path):
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


def media_fragment_to_payload(
    fragment: Any,
    *,
    world_id: str | None = None,
    story_id: str | None = None,
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

            content_type = getattr(rit, "data_type", None)
            payload["media_type"] = content_type.value if content_type is not None else None
            if content_type in _UNSUPPORTED_MEDIA_TYPES:
                payload["unsupported_reason"] = "unsupported_media_type"
                return payload

            prefix = _url_prefix(scope=scope, world_id=world_id, story_id=story_id)
            if prefix is not None:
                payload["url"] = f"{prefix}/{_filename_for_rit(rit)}"
            return payload

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
