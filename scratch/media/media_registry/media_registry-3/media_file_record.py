from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional, ClassVar, Callable

from PIL.Image import Image
from pydantic import model_validator, Field, field_validator, ConfigDict

from tangl.type_hints import Pathlike
from tangl.utils.pixel_avg_hash import pix_avg_hash
from tangl.utils.shelved2 import shelved, clear_shelf
from tangl.utils.file_check_values import compute_file_hash, get_file_mtime
from tangl.media.type_hints import Media
from tangl.media.media_registry.media_record import MediaRecord

class MediaFileRecord(MediaRecord):
    """
    A MediaFileRecord is a subclass of MediaRecord that tracks an on-disk or
    in-memory file.

    On-disk files have a "path" attribute.  In-memory files have a "data" attribute.

    If data is requested for an on-disk file, the file is loaded.  To prevent files
    from being constantly loaded and unloaded for the data hash, the data hash is
    cached/shelved as a separate resource.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: Media = None
    path: Path = None
    mtime: datetime = None
    file_hash: bytes = None

    @model_validator(mode='before')
    @classmethod
    def _compute_defaults_from_path(cls, values) -> dict:
        if "path" in values:
            path = Path( values['path'] )
            if not values.get('label'):
                values['label'] = path.stem
            if 'file_hash' not in values:
                values['file_hash'] = compute_file_hash(path)
            if 'mtime' not in values:
                values['mtime'] = get_file_mtime(path)
        return values

    @field_validator("path", mode="before")
    @classmethod
    def _check_exists(cls, value: Path):
        if value and not value.is_file():
            raise FileNotFoundError
        return value

    def compute_digest(self) -> bytes:
        return self.file_hash


class ImageFileRecord(MediaFileRecord):

    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: Image = None

    def compute_digest(self):
        check_value = ( self.file_hash, self.mtime )
        return MediaFileRecord.compute_px_hash(self.path, check_value=check_value)

    # computing data hashes for images can be slow, so we can cache the results
    shelf_name: ClassVar[str] = "image_hashes"

    @shelved(fn=shelf_name)
    @staticmethod
    def compute_px_hash(path: Pathlike, check_value=None):
        # check value gets passed to the cache for invalidating stale entries
        from PIL import Image
        im = Image.open(path)
        data_hash = pix_avg_hash(im)
        return data_hash

    @classmethod
    def clear_cache(cls):
        clear_shelf(cls.shelf_name)

    @property
    def image(self):
        from PIL import Image
        if self.data is None:
            self.data = Image.open(self.path)
        return self.data
