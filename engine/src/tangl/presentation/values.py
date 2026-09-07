"""Projected display values for presentation surfaces."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from tangl.core.bases import Unstructurable


PrimitiveValue: TypeAlias = str | int | float | bool


class KvRow(Unstructurable):
    """Unified key/value row for scene-bound and projected-state surfaces."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    key: str
    value: PrimitiveValue
    max: PrimitiveValue | None = None
    delta: int | float | None = None
    unit: str | None = None
    hint: Literal["bar", "fraction", "delta", "tag"] | None = None
    emphasis: Literal["ok", "warn", "danger", "subtle"] | None = None
    presentation_hints: dict[str, Any] | None = Field(None, alias="hints")


__all__ = ["KvRow", "PrimitiveValue"]
