from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID


RenPyMediaAction = Literal["scene", "show"]


@dataclass(slots=True, frozen=True)
class RenPyMediaOp:
    """Adapter-local media operation for the Ren'Py demo client."""

    action: RenPyMediaAction
    role: str
    source: str
    tag: str | None = None
    position: str | None = None
    alt_text: str | None = None
    content_format: str | None = None
    source_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class RenPyLine:
    """One narrator or speaker line ready for Ren'Py presentation."""

    text: str
    speaker: str | None = None
    speaker_key: str | None = None
    style_name: str | None = None
    portrait_tag: str | None = None


@dataclass(slots=True, frozen=True)
class RenPyChoice:
    """One StoryTangl choice adapted for a Ren'Py menu."""

    choice_id: UUID
    text: str
    available: bool = True
    unavailable_reason: str | None = None
    accepts: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    choice_payload: Any = None


@dataclass(slots=True)
class RenPyTurn:
    """A step-grouped batch of media, lines, and choices."""

    step: int
    media_ops: list[RenPyMediaOp] = field(default_factory=list)
    lines: list[RenPyLine] = field(default_factory=list)
    choices: list[RenPyChoice] = field(default_factory=list)

