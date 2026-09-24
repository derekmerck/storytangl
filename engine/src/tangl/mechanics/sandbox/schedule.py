"""Schedule matching primitives for sandbox scopes."""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field, field_validator, model_validator

from tangl.core.runtime_op import Effect, Predicate

from .interaction import SandboxInteraction, normalize_runtime_ops
from .time import WorldTime


class ScheduleEntry(BaseModel):
    """One optional time/location/presence gate."""

    label: str = ""
    location: str | None = None
    actor: str | None = None
    period: int | None = None
    run_day: int | None = Field(default=None, gt=0)
    run_day_from: int | None = Field(default=None, gt=0)
    run_day_through: int | None = Field(default=None, gt=0)
    day: int | None = None
    day_of_month: int | None = None
    month: int | None = None
    season: int | None = None
    year: int | None = None

    @model_validator(mode="after")
    def _validate_run_day_window(self) -> "ScheduleEntry":
        if (
            self.run_day_from is not None
            and self.run_day_through is not None
            and self.run_day_through < self.run_day_from
        ):
            raise ValueError("run_day_through must not precede run_day_from")
        if self.run_day is not None and (
            (self.run_day_from is not None and self.run_day < self.run_day_from)
            or (
                self.run_day_through is not None
                and self.run_day > self.run_day_through
            )
        ):
            raise ValueError("run_day must fall within the declared run-day window")
        return self

    def matches_time(self, world_time: WorldTime) -> bool:
        """Return whether the entry's calendar fields match the supplied time."""
        return (
            (self.period is None or world_time.period == self.period)
            and (self.run_day is None or world_time.run_day == self.run_day)
            and (
                self.run_day_from is None
                or world_time.run_day >= self.run_day_from
            )
            and (
                self.run_day_through is None
                or world_time.run_day <= self.run_day_through
            )
            and (self.day is None or world_time.day == self.day)
            and (
                self.day_of_month is None
                or world_time.day_of_month == self.day_of_month
            )
            and (self.month is None or world_time.month == self.month)
            and (self.season is None or world_time.season == self.season)
            and (self.year is None or world_time.year == self.year)
        )

    def matches(
        self,
        world_time: WorldTime,
        *,
        location: str | None = None,
        actors_present: Iterable[str] = (),
    ) -> bool:
        """Return whether this entry applies in the supplied context."""
        if not self.matches_time(world_time):
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
        present = tuple(actors_present)
        return [
            entry
            for entry in self.entries
            if entry.matches(
                world_time,
                location=location,
                actors_present=present,
            )
        ]


class ScheduledEvent(ScheduleEntry):
    """A time/presence gate over a normal sandbox interaction."""

    target: str
    text: str = ""
    journal: str | None = None
    journal_text: str = ""
    activation: str | None = None
    once: bool = False
    return_to_location: bool = False
    availability: list[Predicate] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)

    @field_validator("availability", mode="before")
    @classmethod
    def _normalize_availability(cls, value: object) -> list[Predicate]:
        return normalize_runtime_ops(value, Predicate)

    @field_validator("effects", mode="before")
    @classmethod
    def _normalize_effects(cls, value: object) -> list[Effect]:
        return normalize_runtime_ops(value, Effect)

    def action_text(self) -> str:
        """Return player-facing text for this scheduled event."""
        return self.text or self.label or self.target

    def as_interaction(self, label: str | None = None) -> SandboxInteraction:
        """Return the sandbox interaction primed by this schedule entry."""
        return SandboxInteraction(
            label=label or self.label or self.target,
            text=self.action_text(),
            target=self.target,
            journal_text=self.journal_text or self.journal or "",
            activation=self.activation,
            once=self.once,
            return_to_location=self.return_to_location,
            availability=list(self.availability),
            effects=list(self.effects),
        )


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
