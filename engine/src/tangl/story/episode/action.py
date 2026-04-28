from __future__ import annotations

from typing import Any

from tangl.vm import ResolutionPhase, TraversableEdge


class Action(TraversableEdge):
    """Action()

    Traversable choice edge connecting story blocks.

    Why
    ----
    ``Action`` carries both user-facing choice text and authored successor
    semantics, allowing the compiler and materializer to preserve the narrative
    meaning of redirects, continuations, and interactive choices.
    """

    text: str = ""
    successor_ref: str | None = None
    activation: str | None = None
    payload: Any = None
    accepts: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    journal_text: str | None = None

    @classmethod
    def trigger_phase_from_activation(cls, activation: str | None) -> ResolutionPhase | None:
        """Map authored activation shorthands to vm resolution phases."""
        if activation == "first":
            return ResolutionPhase.PREREQS
        if activation == "last":
            return ResolutionPhase.POSTREQS
        return None
