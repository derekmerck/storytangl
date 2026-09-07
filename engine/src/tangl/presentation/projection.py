"""Portable disclosed-state values for presentation surfaces."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self, TypeAlias

from pydantic import BaseModel, Field, JsonValue, model_validator

from .hints import PresentationHints
from .values import KvRow, PrimitiveValue


class InfoAffordance(BaseModel):
    """Advisory projected-state channel advertised to clients."""

    kind: str
    label: str | None = None
    shortcuts: list[str] = Field(default_factory=list)
    query: dict[str, JsonValue] | None = None


class InfoState(BaseModel):
    """Lightweight projected-state availability marker for one envelope."""

    version: int
    dirty_kinds: list[str] = Field(default_factory=list)
    available_kinds: list[str] = Field(default_factory=list)


class ProjectionRequest(BaseModel):
    """Opaque projected-state request descriptor from a client."""

    kind: str | None = None
    kinds: list[str] = Field(default_factory=list)
    query: dict[str, JsonValue] | None = None

    def requested_kinds(self) -> list[str]:
        """Return requested info kinds in stable first-seen order."""
        requested: list[str] = []

        def append(value: object) -> None:
            if not isinstance(value, str) or not value:
                return
            if value not in requested:
                requested.append(value)

        append(self.kind)
        for kind in self.kinds:
            append(kind)

        query = self.query or {}
        query_kinds = query.get("kinds")
        if isinstance(query_kinds, list):
            for kind in query_kinds:
                append(kind)

        query_kind = query.get("kind")
        append(query_kind)
        return requested


class ScalarValue(BaseModel):
    """Single scalar projected-state payload."""

    value_type: Literal["scalar"] = "scalar"
    value: PrimitiveValue


class KvListValue(BaseModel):
    """Ordered key-value payload."""

    value_type: Literal["kv_list"] = "kv_list"
    items: list[KvRow]


class ProjectedItem(BaseModel):
    """One projected list entry."""

    label: str
    detail: str | None = None
    tags: list[str] = Field(default_factory=list)


class ItemListValue(BaseModel):
    """Ordered projected item list."""

    value_type: Literal["item_list"] = "item_list"
    items: list[ProjectedItem]


class TableValue(BaseModel):
    """Tabular projected-state payload."""

    value_type: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[PrimitiveValue]]

    @model_validator(mode="after")
    def _validate_row_lengths(self) -> Self:
        expected_width = len(self.columns)
        for index, row in enumerate(self.rows):
            if len(row) != expected_width:
                raise ValueError(
                    "table row "
                    f"{index} has {len(row)} values but expected {expected_width} "
                    "to match the declared columns"
                )
        return self


class BadgeListValue(BaseModel):
    """Badge or label collection payload."""

    value_type: Literal["badges"] = "badges"
    items: list[str]


SectionValue: TypeAlias = Annotated[
    ScalarValue | KvListValue | ItemListValue | TableValue | BadgeListValue,
    Field(discriminator="value_type"),
]


class ProjectedSection(BaseModel):
    """One ordered projected runtime-state section."""

    section_id: str
    title: str
    kind: str | None = None
    value: SectionValue
    hints: PresentationHints | None = None


class ProjectedState(BaseModel):
    """Canonical ordered projected-state payload for runtime surfaces."""

    sections: list[ProjectedSection] = Field(default_factory=list)

    def to_dto(self) -> dict[str, Any]:
        """Return the transport DTO projection for projected-state clients."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


__all__ = [
    "BadgeListValue",
    "InfoAffordance",
    "InfoState",
    "ItemListValue",
    "KvListValue",
    "ProjectedItem",
    "ProjectedSection",
    "ProjectedState",
    "ScalarValue",
    "SectionValue",
    "ProjectionRequest",
    "TableValue",
]
