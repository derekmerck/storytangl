from __future__ import annotations
import hashlib
from typing import Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import Field, model_validator, field_validator

from tangl.core.entity import Entity
from .media_data_type import MediaDataType

class MediaRecord(Entity):
    """
    MediaRecords can be dereferenced by the response handler to generate a client-relative path.
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

    @model_validator(mode="after")
    def _set_content_hash(self):
        if self.data:
            self.content_hash = self.compute_data_hash(self.data)
        elif self.path:
            self.content_hash = self.compute_file_hash(self.path)
        else:
            raise ValueError("Must include either data or path in constructor.")

    data_type: MediaDataType = None

    @model_validator(mode="after")
    def _set_data_type(self):
        if not self.data_type:
            if self.path:
                if data_type := MediaDataType.from_path(self.path):
                    self.data_type = data_type
                raise ValueError(f"Unknown media data type for fp {self.path}")
            else:
                raise ValueError("Must include a media data type when passing raw data")

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
