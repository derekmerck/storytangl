from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Self

from tangl.utils.enum_plus import EnumPlusMixin


# File/container declarations, not codec detection or a playback guarantee.
AUDIO_MIME_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
}


class MediaDataType(EnumPlusMixin, Enum):
    MEDIA = "media"  # generic default
    IMAGE = "image"  # a PIL image
    VECTOR = "vector"  # an lxml document

    AUDIO = "audio"  # roles such as music and voice are separate

    TEXT = "text"  # plain text a text client prints as is, such as a world's banner

    VIDEO = "video"  # generic video default, mp4
    OTHER = "other"  # unrecognized media type

    ANIMATION = "animation"

    @classmethod
    def extension_map(cls) -> dict[Self, list[str]]:
        return {
            cls.IMAGE: ["png", "webp", "jpg", "jpeg", "gif", "bmp"],
            cls.VECTOR: ["svg", "ai"],
            cls.AUDIO: list(AUDIO_MIME_TYPES),
            cls.TEXT: ["txt"],
            cls.VIDEO: ["mp4", "mkv", "webm"],
        }

    @classmethod
    def inv_ext_map(cls) -> dict[str, Self]:
        return { vv: k for k, v in cls.extension_map().items() for vv in v }

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        extension = Path(path).suffix or str(path)
        return cls.inv_ext_map().get(extension.lstrip(".").lower(), cls.OTHER)

    @property
    def ext(self) -> str:
        # first entry is default ext
        return self.extension_map()[self][0]
