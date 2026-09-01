from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Self

from tangl.utils.enum_plus import EnumPlusMixin

class MediaDataType(EnumPlusMixin, Enum):
    MEDIA = "media"  # generic default
    IMAGE = "image"  # a PIL image
    VECTOR = "vector"  # an lxml document

    AUDIO = "audio"  # generic audio default, mp3
    SFX = "sound_fx"  # sfx audio
    VOICE = "voice"  # voice over audio
    MUSIC = "music"  # music audio

    VIDEO = "video"  # generic video default, mp4
    OTHER = "other"  # unrecognized media type

    ANIMATION = "animation"

    @classmethod
    def extension_map(cls) -> dict[Self, list[str]]:
        return {
            cls.IMAGE: ["png", "webp", "jpg", "jpeg", "gif", "bmp"],
            cls.VECTOR: ["svg", "ai"],
            cls.AUDIO: ["mp3"],
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
