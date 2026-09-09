from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID


RenPyMediaAction = Literal["scene", "show"]
CHOICE_KEYS = "123456789abcdefghijklmnopqrstuvwyz"


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

    edge_id: UUID
    text: str
    available: bool = True
    unavailable_reason: str | None = None
    blockers: tuple[dict[str, Any], ...] = ()
    cost_previews: tuple[dict[str, Any], ...] = ()
    accepts: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    choice_payload: Any = None


@dataclass(slots=True, frozen=True)
class RenPyMenuChoice:
    """One choice with the marker and key used by the Ren'Py screen."""

    edge_id: UUID
    text: str
    available: bool
    unavailable_reason: str | None
    marker: str
    key: str | None


def choice_key_for_position(choice: RenPyChoice, position: int) -> str | None:
    """Return the accepted key for one presented position, if any."""

    if not choice.available:
        return None
    hotkey = None if choice.ui_hints is None else choice.ui_hints.get("hotkey")
    if isinstance(hotkey, str) and hotkey.strip():
        return hotkey.strip()
    if 1 <= position <= len(CHOICE_KEYS):
        return CHOICE_KEYS[position - 1]
    return None


def present_choices(choices: list[RenPyChoice]) -> list[RenPyMenuChoice]:
    """Add positional markers without dropping locked choices."""

    presented: list[RenPyMenuChoice] = []
    seen: dict[str, tuple[int, RenPyChoice]] = {}
    for position, choice in enumerate(choices, start=1):
        key = choice_key_for_position(choice, position)
        if key is not None:
            previous = seen.get(key)
            if previous is not None:
                previous_position, previous_choice = previous
                raise ValueError(
                    f'Duplicate Ren\'Py choice hotkey "{key}" for positions '
                    f"{previous_position} ({previous_choice.edge_id}) and "
                    f"{position} ({choice.edge_id})"
                )
            seen[key] = (position, choice)
        marker = "x)" if not choice.available else f"{key}." if key else ""
        presented.append(
            RenPyMenuChoice(
                edge_id=choice.edge_id,
                text=choice.text,
                available=choice.available,
                unavailable_reason=choice.unavailable_reason,
                marker=marker,
                key=key,
            )
        )
    return presented


@dataclass(slots=True)
class RenPyTurn:
    """A step-grouped batch of media, lines, and choices."""

    step: int
    media_ops: list[RenPyMediaOp] = field(default_factory=list)
    lines: list[RenPyLine] = field(default_factory=list)
    choices: list[RenPyChoice] = field(default_factory=list)
