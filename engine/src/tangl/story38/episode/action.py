from __future__ import annotations

from typing import Any

from tangl.vm38 import ResolutionPhase, TraversableEdge


class Action(TraversableEdge):
    """Choice edge for story38 blocks."""

    text: str = ""
    successor_ref: str | None = None
    activation: str | None = None
    payload: Any = None

    @classmethod
    def trigger_phase_from_activation(cls, activation: str | None) -> ResolutionPhase | None:
        if activation == "first":
            return ResolutionPhase.PREREQS
        if activation == "last":
            return ResolutionPhase.POSTREQS
        return None
