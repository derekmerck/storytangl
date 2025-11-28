from __future__ import annotations
from typing import Self
from enum import Enum
from pathlib import Path

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
    def extension_map(cls):
        return {
            cls.IMAGE: ["png", "webp", "jpg", "jpeg", "gif", "bmp"],
            cls.VECTOR: ["svg", "ai"],
            cls.AUDIO: ["mp3"],
            cls.VIDEO: ["mp4", "mkv", "webm"],
        }

    @classmethod
    def inv_ext_map(cls):
        return { vv: k for k, v in cls.extension_map().items() for vv in v }

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str):
            value = value.strip('.')
        if value in cls.inv_ext_map():
            return cls.inv_ext_map()[value]
        return cls.OTHER

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        path = Path(path)
        return cls(path.suffix)

    @property
    def ext(self):
        # first entry is default ext
        return self.extension_map()[self][0]
