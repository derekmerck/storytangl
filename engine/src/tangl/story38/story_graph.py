from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core38 import Graph, TemplateRegistry


class StoryGraph38(Graph):
    """Story graph specialization for story38 runtime state."""

    initial_cursor_id: UUID | None = None
    initial_cursor_ids: list[UUID] = Field(default_factory=list)
    locals: dict[str, Any] = Field(default_factory=dict)
    factory: TemplateRegistry | None = Field(default=None, exclude=True)
