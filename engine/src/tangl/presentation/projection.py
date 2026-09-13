"""Portable disclosed-state values for presentation surfaces."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self, TypeAlias

from pydantic import BaseModel, Field, model_validator

from .hints import PresentationHints
from .values import KvRow, PrimitiveValue


class InfoAffordance(BaseModel):
    """Advisory projected-state channel advertised to clients."""

    channel_id: str
    label: str | None = None
    shortcuts: list[str] = Field(default_factory=list)


class InfoState(BaseModel):
    """Lightweight projected-state availability marker for one envelope."""

    version: int
    dirty_channels: list[str] = Field(default_factory=list)
    available_channels: list[str] = Field(default_factory=list)


class ProjectionRequest(BaseModel):
    """Exact projected-state channels selected by a client."""

    channels: list[str] = Field(default_factory=list)

    def requested_channels(self) -> list[str]:
        """Return non-empty channel ids in stable first-seen order."""
        return list(dict.fromkeys(channel for channel in self.channels if channel))


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


class ThemeTokens(BaseModel):
    """Advisory client theme tokens for one color mode."""

    primary: str
    accent: str | None = None
    background: str | None = None


class BrandingValue(BaseModel):
    """Cacheable world branding suggestions; clients remain authoritative."""

    value_type: Literal["branding"] = "branding"
    name: str
    logo_media: str | None = None
    light: ThemeTokens | None = None
    dark: ThemeTokens | None = None


SectionValue: TypeAlias = Annotated[
    (
        ScalarValue
        | KvListValue
        | ItemListValue
        | TableValue
        | BadgeListValue
        | BrandingValue
    ),
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

    channels: list[InfoAffordance] = Field(default_factory=list)
    sections: list[ProjectedSection] = Field(default_factory=list)

    def to_dto(self) -> dict[str, Any]:
        """Return the transport DTO projection for projected-state clients."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


__all__ = [
    "BadgeListValue",
    "BrandingValue",
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
    "ThemeTokens",
]
