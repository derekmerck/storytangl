from __future__ import annotations
from typing import Self
from enum import Enum
from pathlib import Path

class MediaDataType(Enum):
    IMAGE  = "image"   # a PIL image
    VECTOR = "vector"  # an lxml document
    AUDIO  = "audio"   # bytes
    VIDEO  = "video"   # bytes

    @classmethod
    def extension_map(cls):
        return {cls.IMAGE:  "png",
                cls.VECTOR: "svg",
                cls.AUDIO:  "mp3",
                cls.VIDEO:  "mp4"}

    @classmethod
    def inv_ext_map(cls):
        return { v: k for k, v in cls.extension_map().items() }

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str):
            value = value.strip('.')
        if value in cls.inv_ext_map():
            return cls.inv_ext_map()[value]

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        path = Path(path)
        if path.suffix in ['.png', '.jpg', '.jpeg', '.webp']:
            return MediaDataType.IMAGE
        elif path.suffix == '.svg':
            return MediaDataType.VECTOR
        elif path.suffix in ['.mp4', '.mkv', '.webm']:
            return MediaDataType.VIDEO
        elif path.suffix == '.mp3':
            return MediaDataType.AUDIO

    @property
    def ext(self):
        return self.extension_map()[self]
