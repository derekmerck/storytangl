"""Schedule matching primitives for sandbox scopes."""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field

from .time import WorldTime


class ScheduleEntry(BaseModel):
    """One optional time/location/presence gate."""

    label: str = ""
    location: str | None = None
    actor: str | None = None
    period: int | None = None
    day: int | None = None
    day_of_month: int | None = None
    month: int | None = None
    season: int | None = None
    year: int | None = None

    def matches(
        self,
        world_time: WorldTime,
        *,
        location: str | None = None,
        actors_present: Iterable[str] = (),
    ) -> bool:
        """Return whether this entry applies in the supplied context."""
        for field_name in ("period", "day", "day_of_month", "month", "season", "year"):
            expected = getattr(self, field_name)
            if expected is not None and getattr(world_time, field_name) != expected:
                return False

        if self.location is not None and self.location != location:
            return False

        if self.actor is not None and self.actor not in set(actors_present):
            return False

        return True


class Schedule(BaseModel):
    """A small collection of schedule entries with deterministic matching."""

    entries: list[ScheduleEntry] = Field(default_factory=list)

    def matching(
        self,
        world_time: WorldTime,
        *,
        location: str | None = None,
        actors_present: Iterable[str] = (),
    ) -> list[ScheduleEntry]:
        """Return entries matching the supplied time and context."""
        return [
            entry
            for entry in self.entries
            if entry.matches(
                world_time,
                location=location,
                actors_present=actors_present,
            )
        ]


class ScheduledEvent(ScheduleEntry):
    """A schedule-gated selectable event projected as a normal action."""

    target: str
    text: str = ""
    activation: str | None = None
    once: bool = False
    return_to_location: bool = False

    def action_text(self) -> str:
        """Return player-facing text for this scheduled event."""
        return self.text or self.label or self.target


class ScheduledPresence(ScheduleEntry):
    """A schedule-gated actor presence declaration."""

    actor: str

    def matches(
        self,
        world_time: WorldTime,
        *,
        location: str | None = None,
        actors_present: Iterable[str] = (),
    ) -> bool:
        """Return whether this declaration places its actor in the context."""
        payload = self.model_copy(update={"actor": None})
        return ScheduleEntry.matches(
            payload,
            world_time,
            location=location,
            actors_present=actors_present,
        )
