"""Minimal fragment envelope shared by journal and service response surfaces."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import ConfigDict

from tangl.type_hints import Identifier, UnstructuredData

from .record import Record


class BaseFragment(Record):
    """Record-based fragment envelope for journal/content payloads."""

    model_config = ConfigDict(extra="allow")

    fragment_type: str | Enum = "content"
    content: Any = None
    origin_id: Identifier | None = None

    def has_channel(self, name: str) -> bool:
        return f"channel:{name}" in self.tags

    def model_dump(self, **kwargs) -> UnstructuredData:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        data = super().model_dump(**kwargs)
        data["fragment_type"] = self.fragment_type
        return data
