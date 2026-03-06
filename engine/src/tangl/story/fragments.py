from __future__ import annotations

from typing import Any
from typing import Optional
from uuid import UUID

from tangl.core import Record


class Fragment(Record):
    """Base story-level journal fragment."""

    fragment_type: str = "fragment"
    step: int = -1


class ContentFragment(Fragment):
    content: str = ""
    source_id: Optional[UUID] = None
    fragment_type: str = "content"


class ChoiceFragment(Fragment):
    edge_id: Optional[UUID] = None
    text: str = ""
    available: bool = True
    unavailable_reason: str | None = None
    blockers: list[dict[str, Any]] | None = None
    accepts: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    fragment_type: str = "choice"


class MediaFragment(Fragment):
    source_id: Optional[UUID] = None
    payload: dict[str, object] | None = None
    fragment_type: str = "media"


__all__ = ["Fragment", "ContentFragment", "ChoiceFragment", "MediaFragment"]
