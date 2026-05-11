"""Mobile actor facade for sandbox scopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from tangl.story.concepts import Actor
from tangl.story.concepts.asset import HasAssets

from .interaction import SandboxInteraction
from .schedule import Schedule
from .time import WorldTime


class SandboxMobAffordance(BaseModel):
    """Simple action a present sandbox mob can contribute."""

    label: str
    text: str
    journal_text: str = ""
    state_effects: dict[str, Any] = Field(default_factory=dict)


class SandboxMob(HasAssets, Actor):
    """Stable actor-like concept that can be parked in a sandbox location."""

    kind: str = ""
    traits: set[str] = Field(default_factory=set)
    location: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    present_text: str | None = None
    nearby_text: str | None = None
    schedule: Schedule = Field(default_factory=Schedule)
    affordances: list[SandboxMobAffordance] = Field(default_factory=list)
    interactions: list[SandboxInteraction] = Field(default_factory=list)

    def scheduled_location(self, world_time: WorldTime | None = None) -> str:
        """Return the mob location implied by its current schedule."""
        if world_time is None:
            return self.location
        for entry in self.schedule.entries:
            if entry.location is not None and entry.matches_time(world_time):
                return entry.location
        return self.location

    def present_at(
        self,
        location_label: str,
        world_time: WorldTime | None = None,
    ) -> bool:
        """Return whether this mob is currently in the given sandbox location."""
        return self.scheduled_location(world_time) == location_label

    def set_state_value(self, key: str, value: Any) -> Any:
        """Set and return one mutable mob state value."""
        self.state[key] = value
        return value
