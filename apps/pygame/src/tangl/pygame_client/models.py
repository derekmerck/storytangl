"""Adapter-local turn model for the pygame client.

Deliberately a sibling of ``tangl.renpy.models`` rather than a shared type. The
two ports need a second consumer before an adapter layer is worth extracting;
divergences between them are recorded in ``apps/pygame/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True, frozen=True)
class StageImage:
    """One image to draw, keyed by ``media_role`` rather than world identity."""

    role: str
    source: str
    alt_text: str | None = None
    source_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class Line:
    """One narration or attributed line.

    ``speaker is None`` means narration and renders in the narration box;
    a speaker renders as a dialog bubble.
    """

    text: str
    speaker: str | None = None
    manner: str | None = None


@dataclass(slots=True, frozen=True)
class Choice:
    """One selectable choice.

    ``edge_id`` is the only thing the input layer ever commits, so a future
    hotspot resolves to the same payload as the numbered list (Input Parity).
    """

    edge_id: UUID
    text: str
    available: bool = True
    unavailable_reason: str | None = None
    payload: Any = None


@dataclass(slots=True)
class Turn:
    """One step's worth of images, lines, and choices."""

    step: int
    images: list[StageImage] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    choices: list[Choice] = field(default_factory=list)
