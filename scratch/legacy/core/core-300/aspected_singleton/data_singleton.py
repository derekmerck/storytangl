import logging
from typing import Optional, Self
from pathlib import Path
import io

from pydantic import BaseModel

from tangl.type_hints import Identifier
from .singleton import Singleton

logger = logging.getLogger(__name__)

class DataSingleton(Singleton, BaseModel):
    """
    Singleton based on content hash of binary data.
    Can be initialized directly with data or deferred for loading.
    """
    data: bytes = None
    content_type: Optional[str] = None  # Optional MIME type or ext
    source: str = None                  # Optional source tracking

    @classmethod
    def compute_digest(cls, *, data: bytes = None, **kwargs) -> Optional[bytes]:
        """Return None if data not yet available to allow deferred digest"""
        logger.debug("Setting digest (data)")
        if data is None:
            # not ready yet
            return
        return cls.hash_value(data)

    @classmethod
    def from_file(cls, path: Path | str, content_type: str | None = None) -> Self:
        """Create instance from file path"""
        path = Path(path)
        with open(path, 'rb') as f:
            data = f.read()
        return cls(
            data=data,
            content_type=content_type or path.suffix.lstrip('.'),
            source=str(path)
        )

    @classmethod
    def from_stream(cls, stream: io.IOBase, content_type: str = None) -> Self:
        """Create instance from file-like object"""
        if isinstance(stream, io.TextIOBase):
            data = stream.read().encode('utf-8')
        else:
            data = stream.read()
        return cls(data=data, content_type=content_type)

    def size(self) -> int:
        """Return size of data in bytes"""
        return len(self.data) if self.data else 0

    def _filter_by_content_type(self, content_type: str) -> bool:
        return self.content_type == content_type

    def _get_identifiers(self) -> set[Identifier]:
        if self.source:
            return { self.source }
