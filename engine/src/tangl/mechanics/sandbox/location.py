"""Location-hub facade for sandbox mechanics."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from tangl.core import Token, contribute_ns
from tangl.story import MenuBlock
from tangl.story.concepts.asset import HasAssets

from .facets import ContainerFacet, LockableFacet, OpenableFacet
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


class SandboxFixture(HasAssets):
    """Place-bound sandbox fixture composed from typed capability facets."""

    label: str
    name: str = ""
    openable: OpenableFacet | None = None
    lockable: LockableFacet | None = None
    container: ContainerFacet | None = None

    @property
    def locked(self) -> bool:
        """Return whether the fixture is currently locked."""
        return bool(self.lockable and self.lockable.is_locked)

    @property
    def open(self) -> bool:
        """Return whether the fixture is currently open."""
        return bool(self.openable and self.openable.is_open)

    @property
    def key(self) -> str | None:
        """Return the key label required by the lock, if any."""
        if self.lockable is None:
            return None
        return self.lockable.key

    def action_text(self) -> str:
        """Return player-facing unlock action text."""
        target_name = self.name or self.label
        if self.lockable and self.lockable.unlock_action_text:
            return self.lockable.unlock_action_text
        return f"Unlock {target_name}"

    def lock_text_label(self) -> str:
        """Return player-facing lock action text."""
        target_name = self.name or self.label
        if self.lockable and self.lockable.lock_action_text:
            return self.lockable.lock_action_text
        return f"Lock {target_name}"

    def open_text_label(self) -> str:
        """Return player-facing open action text."""
        target_name = self.name or self.label
        if self.openable and self.openable.open_action_text:
            return self.openable.open_action_text
        return f"Open {target_name}"

    def close_text_label(self) -> str:
        """Return player-facing close action text."""
        target_name = self.name or self.label
        if self.openable and self.openable.close_action_text:
            return self.openable.close_action_text
        return f"Close {target_name}"

    def can_unlock(self, *, has_key: Callable[[str], bool]) -> bool:
        """Return whether the fixture can currently unlock."""
        if self.lockable is None:
            return False
        return self.lockable.can_unlock(has_key=has_key)

    def unlock(self) -> None:
        """Unlock the fixture."""
        if self.lockable is None:
            raise ValueError(f"Fixture {self.label!r} is not lockable")
        self.lockable.unlock()

    def can_lock(self, *, has_key: Callable[[str], bool]) -> bool:
        """Return whether the fixture can currently lock."""
        if self.lockable is None:
            return False
        return self.lockable.can_lock(has_key=has_key)

    def lock(self) -> None:
        """Lock the fixture."""
        if self.lockable is None:
            raise ValueError(f"Fixture {self.label!r} is not lockable")
        self.lockable.lock()

    def can_open(self, *, has_key: Callable[[str], bool]) -> bool:
        """Return whether the fixture can currently open."""
        _ = has_key
        if self.openable is None:
            return False
        return self.openable.can_open(locked=self.locked)

    def open_fixture(self) -> None:
        """Open the fixture."""
        if self.openable is None:
            raise ValueError(f"Fixture {self.label!r} is not openable")
        self.openable.open()
        if self.container is not None:
            self.container.open()

    def can_close(self) -> bool:
        """Return whether the fixture can currently close."""
        return bool(self.openable and self.openable.can_close())

    def close_fixture(self) -> None:
        """Close the fixture."""
        if self.openable is None:
            raise ValueError(f"Fixture {self.label!r} is not openable")
        self.openable.close()
        if self.container is not None:
            self.container.close()

    def container_accessible(self) -> bool:
        """Return whether the fixture's container contents are reachable."""
        if self.container is None:
            return False
        if self.locked:
            return False
        if self.openable is not None and not self.open:
            return False
        if self.openable is None and not self.container.is_open:
            return False
        return True

    def can_receive_asset(self, asset: Token, giver: HasAssets | None = None) -> bool:
        """Return whether this fixture can receive a discrete asset."""
        _ = giver
        if self.container is None or not self.container_accessible():
            return False
        return self.container.can_accept_asset(asset, current_count=len(self.assets))

    def can_give_asset(self, asset: Token, receiver: HasAssets | None = None) -> bool:
        """Return whether this fixture can release a discrete asset."""
        _ = receiver
        if self.container is None or not self.container_accessible():
            return False
        return self.has_asset(asset)

    @property
    def unlock_text(self) -> str:
        """Return journal text for unlocking."""
        if self.lockable is None:
            return ""
        return self.lockable.unlock_text

    @property
    def lock_text(self) -> str:
        """Return journal text for locking."""
        if self.lockable is None:
            return ""
        return self.lockable.lock_text

    @property
    def open_text(self) -> str:
        """Return journal text for opening."""
        if self.openable is None:
            return ""
        return self.openable.open_text

    @property
    def close_text(self) -> str:
        """Return journal text for closing."""
        if self.openable is None:
            return ""
        return self.openable.close_text


class SandboxLocation(HasAssets, MenuBlock):
    """A visitable dynamic hub with location links and present assets."""

    links: dict[str, str | SandboxExit] = Field(default_factory=dict)
    scheduled_events: list[ScheduledEvent] = Field(default_factory=list)
    fixtures: list[SandboxFixture] = Field(default_factory=list)
    visibility_rules: list[SandboxVisibilityRule] = Field(default_factory=list)
    sandbox_scope: str | None = None
    location_name: str = ""
    light: bool = False
    dark_text: str | None = None
    wait_enabled: bool | None = None
    wait_text: str | None = None
    wait_turn_delta: int | None = None

    def fixture_by_label(self, label: str) -> SandboxFixture:
        """Return the named local fixture."""
        for fixture in self.fixtures:
            if fixture.label == label:
                return fixture
        raise KeyError(f"Unknown fixture: {label}")

    def unlock_fixture(self, label: str) -> SandboxFixture:
        """Unlock and return the named fixture."""
        fixture = self.fixture_by_label(label)
        fixture.unlock()
        return fixture

    def lock_fixture(self, label: str) -> SandboxFixture:
        """Lock and return the named fixture."""
        fixture = self.fixture_by_label(label)
        fixture.lock()
        return fixture

    def open_fixture(self, label: str) -> SandboxFixture:
        """Open and return the named fixture."""
        fixture = self.fixture_by_label(label)
        fixture.open_fixture()
        return fixture

    def close_fixture(self, label: str) -> SandboxFixture:
        """Close and return the named fixture."""
        fixture = self.fixture_by_label(label)
        fixture.close_fixture()
        return fixture

    @contribute_ns
    def provide_sandbox_location_symbols(self) -> dict[str, Any]:
        """Publish location metadata to the gathered namespace."""
        payload: dict[str, Any] = {
            "current_location": self,
            "current_location_label": self.get_label(),
            "current_location_name": self.location_name or self.get_label(),
            "sandbox_fixtures": {fixture.label: fixture for fixture in self.fixtures},
        }
        if self.sandbox_scope:
            payload["sandbox_scope"] = self.sandbox_scope
        return payload
