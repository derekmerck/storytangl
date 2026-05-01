"""Mobile actor facade for sandbox scopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from tangl.story.concepts import Actor


class SandboxMobAffordance(BaseModel):
    """Simple action a present sandbox mob can contribute."""

    label: str
    text: str
    journal_text: str = ""
    state_effects: dict[str, Any] = Field(default_factory=dict)


class SandboxMob(Actor):
    """Stable actor-like concept that can be parked in a sandbox location."""

    kind: str = ""
    traits: set[str] = Field(default_factory=set)
    location: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    present_text: str | None = None
    nearby_text: str | None = None
    affordances: list[SandboxMobAffordance] = Field(default_factory=list)

    def present_at(self, location_label: str) -> bool:
        """Return whether this mob is currently in the given sandbox location."""
        return self.location == location_label

    def set_state_value(self, key: str, value: Any) -> Any:
        """Set and return one mutable mob state value."""
        self.state[key] = value
        return value
