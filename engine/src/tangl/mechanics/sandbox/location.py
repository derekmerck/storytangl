"""Location-hub facade for sandbox mechanics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from tangl.core import contribute_ns
from tangl.story import MenuBlock
from tangl.story.concepts.asset import HasAssets

from .schedule import ScheduledEvent
from .visibility import SandboxVisibilityRule


SANDBOX_DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
    "u": "up",
    "d": "down",
    "enter": "in",
    "inside": "in",
    "exit": "out",
    "outside": "out",
}


def normalize_sandbox_direction(direction: str) -> str:
    """Return the canonical sandbox direction for a link key."""
    normalized = direction.strip().lower().replace(" ", "_")
    return SANDBOX_DIRECTION_ALIASES.get(normalized, normalized)


class SandboxExit(BaseModel):
    """Structured egress declaration for sandbox location links."""

    target: str | None = None
    text: str | None = None
    kind: str | None = None
    journal_text: str | None = None
    through: str | None = None


class SandboxLockable(BaseModel):
    """Minimal lockable local fixture projected into sandbox choices."""

    label: str
    name: str = ""
    key: str = "key"
    locked: bool = True
    openable: bool = False
    open: bool = False
    unlock_text: str = "The key turns with a click. The lock opens."
    unlock_action_text: str = ""
    open_text: str = "Opened."
    close_text: str = "Closed."
    open_action_text: str = ""
    close_action_text: str = ""

    def action_text(self) -> str:
        """Return player-facing unlock action text."""
        target_name = self.name or self.label
        return self.unlock_action_text or f"Unlock {target_name}"

    def open_text_label(self) -> str:
        """Return player-facing open action text."""
        target_name = self.name or self.label
        return self.open_action_text or f"Open {target_name}"

    def close_text_label(self) -> str:
        """Return player-facing close action text."""
        target_name = self.name or self.label
        return self.close_action_text or f"Close {target_name}"


class SandboxLocation(HasAssets, MenuBlock):
    """A visitable dynamic hub with location links and present assets."""

    links: dict[str, str | SandboxExit] = Field(default_factory=dict)
    scheduled_events: list[ScheduledEvent] = Field(default_factory=list)
    lockables: list[SandboxLockable] = Field(default_factory=list)
    visibility_rules: list[SandboxVisibilityRule] = Field(default_factory=list)
    sandbox_scope: str | None = None
    location_name: str = ""
    light: bool = False
    dark_text: str | None = None
    wait_enabled: bool | None = None
    wait_text: str | None = None
    wait_turn_delta: int | None = None

    def unlock_lockable(self, label: str) -> SandboxLockable:
        """Unlock and return the named lockable object."""
        for lockable in self.lockables:
            if lockable.label == label:
                lockable.locked = False
                return lockable
        raise KeyError(f"Unknown lockable: {label}")

    def open_lockable(self, label: str) -> SandboxLockable:
        """Open and return the named lockable object."""
        for lockable in self.lockables:
            if lockable.label == label:
                lockable.open = True
                return lockable
        raise KeyError(f"Unknown lockable: {label}")

    def close_lockable(self, label: str) -> SandboxLockable:
        """Close and return the named lockable object."""
        for lockable in self.lockables:
            if lockable.label == label:
                lockable.open = False
                return lockable
        raise KeyError(f"Unknown lockable: {label}")

    @contribute_ns
    def provide_sandbox_location_symbols(self) -> dict[str, Any]:
        """Publish location metadata to the gathered namespace."""
        payload: dict[str, Any] = {
            "current_location": self,
            "current_location_label": self.get_label(),
            "current_location_name": self.location_name or self.get_label(),
            "sandbox_lockables": {lockable.label: lockable for lockable in self.lockables},
        }
        if self.sandbox_scope:
            payload["sandbox_scope"] = self.sandbox_scope
        return payload
