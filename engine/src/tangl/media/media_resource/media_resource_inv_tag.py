from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Optional, Self
from uuid import UUID

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from tangl.core import HasContent, RegistryAware
from tangl.core.bases import Hash, is_identifier
from tangl.media.media_data_type import MediaDataType
from tangl.utils.hashing import compute_data_hash
from tangl.utils.shelved2 import clear_shelf, shelved

# RITs are _technically_ resource-type Nodes when used in a graph,
# but they can also be used without a graph, so it makes more sense
# as an Entity rather than a GraphItem.


class _ContentHash(bytes):
    """Compat shim: bytes-like value that also supports legacy call syntax."""

    __name__ = "content_hash"

    def __new__(cls, value: Hash) -> "_ContentHash":
        return super().__new__(cls, bytes(value))

    def __call__(self) -> Hash:
        return bytes(self)


class MediaRITStatus(str, Enum):
    """Lifecycle state for story-scoped generated media."""

    PENDING = "pending"
    RUNNING = "running"
    RESOLVED = "resolved"
    FAILED = "failed"


class MediaPersistencePolicy(str, Enum):
    """Persistence classification for generated media."""

    EPHEMERAL = "ephemeral"
    CACHEABLE = "cacheable"
    STORY_CANONICAL = "story_canonical"
    EXTERNAL_REFERENCE = "external_reference"


class MediaResourceInventoryTag(RegistryAware, HasContent):
    """
    MediaResourceInventoryTags track data resources, in-mem or on disk.

    MRT's for media data can be dereferenced by the response handler at the
    service layer to generate a client-relative media path.
    """
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    # frozen false, so it can run 'after' model validators

    # todo: handle data stored in other dbs like path is indirect reference to file data?
    #       Annotate data with cms info?
    path: Optional[Path] = None
    data: Optional[Any] = None
    # Must have one or the other if no pre-computed content hash
    preset_content_hash: bytes | None = Field(default=None, alias="content_hash")
    status: MediaRITStatus = MediaRITStatus.RESOLVED
    job_id: str | None = None
    persistence_policy: MediaPersistencePolicy = MediaPersistencePolicy.CACHEABLE
    adapted_spec: dict[str, Any] | None = None
    adapted_spec_hash: str | None = Field(
        default=None,
        validation_alias=AliasChoices("adapted_spec_hash", "spec_fingerprint"),
    )
    derivation_spec: dict[str, Any] | None = None
    execution_spec: dict[str, Any] | None = None
    execution_spec_hash: str | None = None
    worker_id: str | None = None
    generated_at: datetime | None = None
    source_step_id: UUID | None = None

    req_hash: ClassVar[bool] = True

    @classmethod
    def _get_hashable_content(cls, data: dict) -> Any:
        if "content_hash" in data:
            return data["content_hash"]
        if 'data' in data:
            return data['data']
        elif 'path' in data:
            return compute_data_hash(Path(data['path']))
        raise ValueError("Must specify either a content hash, the data, or path")

    def get_hashable_content(self) -> Any:
        if self.data is not None:
            return self.data
        if self.path is not None:
            return compute_data_hash(self.path)
        raise ValueError("Must specify either media data or a media path")

    data_type: MediaDataType = None

    @field_validator("preset_content_hash", mode="before")
    @classmethod
    def _normalize_content_hash(cls, value: Any) -> bytes | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            token = value.strip()
            if token.startswith("0x"):
                token = token[2:]
            try:
                return bytes.fromhex(token)
            except ValueError as exc:
                raise ValueError("content_hash must be bytes or a valid hex string") from exc
        raise TypeError("content_hash must be bytes or a valid hex string")

    @model_validator(mode="after")
    def _validate_required_source(self):
        status = getattr(self, "status", MediaRITStatus.RESOLVED)
        if (
            status == MediaRITStatus.RESOLVED
            and self.data is None
            and self.path is None
            and self.preset_content_hash is None
        ):
            raise ValueError("Must specify either a content hash, media data, or media path")
        return self

    @model_validator(mode="after")
    def _set_data_type(self):
        status = getattr(self, "status", MediaRITStatus.RESOLVED)
        if status != MediaRITStatus.RESOLVED and self.data_type is None:
            return self
        if not self.data_type:
            if self.path:
                if data_type := MediaDataType.from_path(self.path):
                    self.data_type = data_type
                else:
                    raise ValueError(f"Unknown data type for fp {self.path}")
            elif self.data is not None:
                raise ValueError("Must include a data type when passing raw data")
        return self

    def _resolve_content_hash(self) -> Hash:
        preset_hash = getattr(self, "preset_content_hash", None)
        if preset_hash is not None:
            return preset_hash
        status = getattr(self, "status", MediaRITStatus.RESOLVED)
        if status != MediaRITStatus.RESOLVED:
            raise ValueError("Pending media does not have a content hash yet")
        return super().content_hash()

    @property
    def content_hash(self) -> _ContentHash:
        try:
            return _ContentHash(self._resolve_content_hash())
        except ValueError:
            return _ContentHash(b"")

    @is_identifier
    def get_content_hash(self) -> Hash | None:
        try:
            return self._resolve_content_hash()
        except ValueError:
            return None

    @is_identifier
    def get_adapted_spec_hash(self) -> str | None:
        return getattr(self, "adapted_spec_hash", None)

    @is_identifier
    def get_spec_fingerprint(self) -> str | None:
        return getattr(self, "adapted_spec_hash", None)

    @is_identifier
    def get_execution_spec_hash(self) -> str | None:
        return getattr(self, "execution_spec_hash", None)

    @property
    def spec_fingerprint(self) -> str | None:
        """Compatibility alias for the old Phase 1 fingerprint field."""
        return getattr(self, "adapted_spec_hash", None)

    @spec_fingerprint.setter
    def spec_fingerprint(self, value: str | None) -> None:
        self.adapted_spec_hash = value

    inventory_time: datetime = Field(init=False, default_factory=datetime.now)
    expiry: Optional[datetime | timedelta] = None

    @model_validator(mode='after')
    def _convert_expiry_time_delta(self):
        if isinstance(self.expiry, timedelta):
            self.expiry = self.inventory_time + self.expiry
        return self

    def has_expired(self, *args, **kwargs) -> bool:
        # for matching `find(expired=True)`
        expiry = getattr(self, "expiry", None)
        return expiry is not None and expiry < datetime.now()

    # this is to avoid recomputing hash values for static inventories
    # todo: should change it to cache the value keyed on (fn, mdate, size)
    @shelved(fn="rits")
    @staticmethod
    def _from_path(cls, path: Path) -> MediaResourceInventoryTag:
        record = cls(path=path)
        record.preset_content_hash = record._resolve_content_hash()
        return record

    @classmethod
    def from_source(cls, item: Path | str) -> Self:
        if isinstance(item, (Path, str)):
            path = Path(item)
            stat = path.stat()
            return cls._from_path(
                cls,
                path,
                check_value=(stat.st_mtime_ns, stat.st_size),
            )
        raise NotImplementedError("Can only load from file paths currently")

    @classmethod
    def clear_from_source_cache(cls):
        clear_shelf("rits")
