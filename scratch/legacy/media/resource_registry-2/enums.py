from __future__ import annotations
from enum import Enum


class ResourceDataType(Enum):
    IMAGE  = "image"   # a PIL image
    VECTOR = "vector"  # an lxml document
    AUDIO  = "audio"   # bytes

    @classmethod
    def extension_map(cls):
        return {cls.IMAGE:  "png",
                cls.VECTOR: "svg",
                cls.AUDIO:  "mp3"}

    @classmethod
    def inv_ext_map(cls):
        return { v: k for k, v in cls.extension_map().items() }

    @classmethod
    def _missing_(cls, value: object) -> ResourceDataType:
        if isinstance(value, str):
            value = value.strip('.')
        if value in cls.inv_ext_map():
            return cls.inv_ext_map()[value]

    @property
    def ext(self):
        return self.extension_map()[self]
