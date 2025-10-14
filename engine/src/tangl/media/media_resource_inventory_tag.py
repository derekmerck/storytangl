from __future__ import annotations

"""Filesystem-backed media resource inventory tags."""

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, model_validator

from tangl.core.entity import Entity
from tangl.media.enums import MediaDataType
from tangl.type_hints import Hash
from tangl.utils.hashing import compute_data_hash, uuid_from_secret


class MediaResourceInventoryTag(Entity):
    """MediaResourceInventoryTag(uid: UUID, path: Path | None, media_type: MediaDataType)

    Immutable record of a discovered media asset.

    Why
    ---
    Media discovery inventories local files so that downstream services can
    reference them via deterministic identifiers.  The
    :class:`MediaResourceInventoryTag` captures the metadata required to resolve a
    file and to match it using tags or media characteristics.

    Key Features
    ------------
    * **Deterministic identifiers** – UIDs are derived from the file's content
      hash, allowing stable references across discovery runs.
    * **Tag indexing** – Filename-derived tags enable lightweight querying prior
      to full-text indexing.
    * **Filesystem provenance** – Records store the discovery source so the
      service layer can produce URLs later.

    API
    ---
    - :meth:`from_path`
    - :meth:`matches`
    - :attr:`is_resolved`
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    uid: UUID = Field(default_factory=uuid4, json_schema_extra={"is_identifier": True})
    content_hash: Optional[Hash] = Field(
        None,
        json_schema_extra={"is_identifier": True},
    )
    path: Optional[Path] = Field(
        None,
        json_schema_extra={"is_identifier": True},
    )
    role: Optional[str] = None
    media_type: MediaDataType = Field(default=MediaDataType.UNKNOWN)
    status: Literal["resolved"] = "resolved"
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    @classmethod
    def _coerce_media_type(cls, data: Any) -> Any:
        """Support legacy ``data_type`` keyword arguments."""

        if isinstance(data, dict) and "media_type" not in data and "data_type" in data:
            data = {**data, "media_type": data["data_type"]}
        return data

    @property
    def data_type(self) -> MediaDataType:
        """Alias for backwards compatibility with legacy callers."""

        return self.media_type

    @data_type.setter
    def data_type(self, value: MediaDataType) -> None:
        self.media_type = value

    @classmethod
    def from_path(
        cls,
        path: Path | str,
        tags: Optional[Iterable[str]] = None,
        role: str | None = None,
    ) -> "MediaResourceInventoryTag":
        """Create a resource inventory tag from ``path`` on disk."""

        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(resolved)
        if not resolved.is_file():
            raise ValueError(f"{resolved} is not a file")

        content_hash = compute_data_hash(resolved)
        try:
            media_type = MediaDataType.from_path(resolved)
        except ValueError:
            media_type = MediaDataType.UNKNOWN

        stem = resolved.stem.replace("_", "-").lower()
        auto_tags = {chunk for chunk in stem.split("-") if chunk}
        provided_tags = set(tags or [])
        all_tags = auto_tags | provided_tags

        return cls(
            uid=uuid_from_secret(content_hash),
            path=resolved,
            content_hash=content_hash,
            media_type=media_type,
            role=role,
            tags=all_tags,
            source=f"filesystem:{resolved.parent}",
        )

    def matches(self, **criteria) -> bool:  # type: ignore[override]
        """Match registry queries with tag-subset semantics."""

        extra = dict(criteria)
        tag_filter = extra.pop("tags", None)
        if tag_filter is not None:
            if isinstance(tag_filter, str):
                required = {tag_filter}
            else:
                required = set(tag_filter)
            if not required.issubset(self.tags):
                return False
        return super().matches(**extra)

    @property
    def is_resolved(self) -> bool:
        """RITs generated from filesystem discovery are always resolved."""

        return True
