from __future__ import annotations
from typing import Self
import hashlib
from typing import Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import Field, field_serializer, field_validator, model_validator

from tangl.utils.shelved2 import shelved, clear_shelf
from tangl.utils.hashing import compute_data_hash
from tangl.core.entity import Entity
from tangl.media.media_data_type import MediaDataType

# todo: these are Records now

# RITs are _technically_ resource-type Nodes when used in a graph,
# but they can also be used without a graph, so it makes more sense
# as an Entity rather than a GraphItem.
class MediaResourceInventoryTag(Entity):
    """
    MediaResourceInventoryTags track data resources, in-mem or on disk.

    MRT's for media data can be dereferenced by the response handler at the
    service layer to generate a client-relative media path.
    """
    # todo: handle data stored in other dbs?  Annotate data with cms info?
    path: Optional[Path] = None
    data: Optional[Any] = None
    # Must have one or the other if no pre-computed content hash
    content_hash: bytes | None = Field(None, json_schema_extra={'is_identifier': True})

    @field_serializer("content_hash")
    def serialize_hash(self, value: bytes | None) -> str | None:
        return value.hex() if value is not None else None

    @field_validator("content_hash", mode="before")
    @classmethod
    def parse_hash(cls, value: Any) -> bytes | None:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return bytes.fromhex(value)
            except ValueError as exc:
                msg = f"Invalid hex content_hash: {value!r}"
                raise ValueError(msg) from exc
        return value

    @model_validator(mode="before")
    @classmethod
    def _set_content_hash(cls, data: Any) -> bytes:
        if 'content_hash' not in data:
            if 'data' in data:
                content_hash = compute_data_hash(data['data'])
            elif 'path' in data:
                path = Path(data['path'])
                content_hash = compute_data_hash(path)
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
                    raise ValueError(f"Unknown data type for fp {self.path}")
            else:
                raise ValueError("Must include a data type when passing raw data")
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

    # this is to avoid recomputing hash values for static inventories
    # todo: should change it to cache the value keyed on (fn, mdate, size)
    @shelved(fn="rits")
    @staticmethod
    def _from_path(cls, path: Path) -> MediaResourceInventoryTag:
        return cls(path=path)

    @classmethod
    def from_source(cls, item: Path) -> Self:
        if isinstance(item, (Path, str)):
            mtime = item.stat().st_mtime
            return cls._from_path(cls, item, check_value=mtime)
        raise NotImplementedError("Can only load from file paths currently")

    @classmethod
    def clear_from_source_cache(cls):
        clear_shelf("rits")
