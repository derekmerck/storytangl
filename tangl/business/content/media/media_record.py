from __future__ import annotations
from typing import Self
import hashlib
from typing import Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import Field, model_validator

from tangl.utils.shelved2 import shelved
from tangl.business.core import Entity
from tangl.service.response.media_fragment import MediaResponseFragment
from .media_data_type import MediaDataType

class MediaRecord(Entity):
    """
    MediaRecords can be dereferenced by the response handler at the service layer
    to generate a client-relative media path.
    """
    path: Optional[Path] = None
    data: Optional[Any] = None
    # Must have one or the other

    @classmethod
    def compute_file_hash(cls, path: Path) -> bytes:
        """Quick file hash for change detection"""
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(64 * 1024), b''):
                hasher.update(chunk)
        return hasher.digest()

    @classmethod
    def compute_data_hash(cls, data: Any) -> bytes:
        if isinstance(data, bytes):
            return hashlib.sha224(data).digest()

    @model_validator(mode="before")
    @classmethod
    def _set_content_hash(cls, data: Any) -> bytes:
        if 'content_hash' not in data:
            if 'data' in data:
                content_hash = cls.compute_data_hash(data['data'])
            elif 'path' in data:
                content_hash = cls.compute_file_hash(data['path'])
            else:
                raise ValueError("Must include a content hash, data, or a path in constructor.")
            data['content_hash'] = content_hash
        return data

    data_type: MediaDataType = None

    @model_validator(mode="after")
    def _set_data_type(self):
        if not self.data_type:
            if self.path:
                if data_type := MediaDataType.from_path(self.path):
                    self.data_type = data_type
                else:
                    raise ValueError(f"Unknown media data type for fp {self.path}")
            else:
                raise ValueError("Must include a media data type when passing raw data")
        return self

    inventory_time: datetime = Field(init=False, default_factory=datetime.now)
    expiry: Optional[datetime | timedelta] = None

    @model_validator(mode='after')
    def _convert_expiry_time_delta(self):
        if isinstance(self.expiry, timedelta):
            self.expiry = self.inventory_time + self.expiry
        return self

    def has_expired(self, *args, **kwargs) -> bool:
        # for matching `find(expired=True)`
        return self.expiry < datetime.now()

    @shelved(fn="media_records")
    @staticmethod
    def _from_path(cls, path: Path) -> MediaRecord:
        return cls(path=path)

    @classmethod
    def from_source(cls, item: Path | MediaDataType) -> Self:
        if isinstance(item, (Path, str)):
            mtime = item.stat().st_mtime
            return cls._from_path(cls, item, check_value=mtime)
        raise NotImplementedError("Can only handle paths right now.")

    def to_response_fragment(self) -> MediaResponseFragment:
        # todo: if this is a file path, it needs to be converted by a response handler to a url path
        #       note that the path provides an identifier for a media record lookup (or just
        #       save the record here?)
        fragment = MediaResponseFragment(
            type=self.data_type.value or "media",
            content=self.path or self.data,
            format="url" if self.path else "data",
        )
        return fragment

