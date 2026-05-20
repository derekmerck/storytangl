"""Mutable future-event list for deterministic simulations."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core import Entity, Registry, Selector
from tangl.core.bases import BaseModelPlus, HasOrder


class SimulationEvent(HasOrder, Entity):
    """Exact future event ordered by normalized turn and insertion sequence."""

    at_turn: int
    kind: str
    target: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    def sort_key(self) -> tuple[int, int]:
        """Return deterministic future-event-list ordering."""
        return (self.at_turn, self.seq)


class EventCalendar(BaseModelPlus):
    """Tiny future-event list backed by core `Registry` selection and sorting."""

    registry: Registry[SimulationEvent] = Field(default_factory=Registry)

    def push(self, event: SimulationEvent) -> SimulationEvent:
        """Add one event and return it for caller bookkeeping."""
        self.registry.add(event)
        return event

    def peek_next(self) -> SimulationEvent | None:
        """Return the next event without mutating the calendar."""
        return self.registry.find_one(sort_key=lambda event: event.sort_key())

    def pop_next(self) -> SimulationEvent | None:
        """Remove and return the next event."""
        event = self.peek_next()
        if event is None:
            return None
        self.registry.remove(event.uid)
        return event

    def peek_turn(self) -> int | None:
        """Return the next event turn, or ``None`` when empty."""
        event = self.peek_next()
        return event.at_turn if event is not None else None

    def events(self) -> list[SimulationEvent]:
        """Return pending events in future-event-list order."""
        return list(self.registry.find_all(sort_key=lambda event: event.sort_key()))

    def __len__(self) -> int:
        return len(self.registry.members)

    def is_empty(self) -> bool:
        """Return whether the calendar has no pending events."""
        return len(self) == 0

    def find_by_kind(self, kind: str) -> list[SimulationEvent]:
        """Return pending events of one kind in calendar order."""
        return list(
            self.registry.find_all(
                Selector(kind=kind),
                sort_key=lambda event: event.sort_key(),
            )
        )
