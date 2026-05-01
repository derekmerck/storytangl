"""Typed sandbox capability facets lowered from compact authoring traits."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, Field

from tangl.core import Token
from tangl.story.concepts.asset import HasAssets


class SwitchState(Protocol):
    """Mutable on/off state carried by a switchable runtime surface."""

    lit: bool


class OpenableFacet(BaseModel):
    """Open/close state and policy for a sandbox fixture."""

    is_open: bool = False
    open_text: str = "Opened."
    close_text: str = "Closed."
    open_action_text: str = ""
    close_action_text: str = ""

    def can_open(self, *, locked: bool = False) -> bool:
        """Return whether this facet can currently open."""
        return not self.is_open and not locked

    def can_close(self) -> bool:
        """Return whether this facet can currently close."""
        return self.is_open

    def open(self) -> None:
        """Mark this facet open."""
        self.is_open = True

    def close(self) -> None:
        """Mark this facet closed."""
        self.is_open = False


class LockableFacet(BaseModel):
    """Lock/unlock state and key policy for a sandbox fixture."""

    is_locked: bool = True
    key: str | None = "key"
    unlock_text: str = "The key turns with a click. The lock opens."
    unlock_action_text: str = ""

    def can_unlock(self, *, has_key: Callable[[str], bool]) -> bool:
        """Return whether this facet can currently unlock."""
        if not self.is_locked:
            return False
        return self.key is None or has_key(self.key)

    def unlock(self) -> None:
        """Mark this facet unlocked."""
        self.is_locked = False

    def can_lock(self, *, has_key: Callable[[str], bool]) -> bool:
        """Return whether this facet can currently lock."""
        if self.is_locked:
            return False
        return self.key is None or has_key(self.key)

    def lock(self) -> None:
        """Mark this facet locked."""
        self.is_locked = True


class SwitchableFacet(BaseModel):
    """On/off policy for a sandbox asset."""

    def can_switch_on(self, *, is_on: bool) -> bool:
        """Return whether the surface can switch on."""
        return not is_on

    def can_switch_off(self, *, is_on: bool) -> bool:
        """Return whether the surface can switch off."""
        return is_on

    def switch_on(self, state: SwitchState) -> None:
        """Switch the supplied state-bearing surface on."""
        state.lit = True

    def switch_off(self, state: SwitchState) -> None:
        """Switch the supplied state-bearing surface off."""
        state.lit = False


class LightSourceFacet(BaseModel):
    """Illumination policy for a sandbox asset."""

    requires_switch: bool = True

    def illuminates(self, *, is_on: bool, switchable: SwitchableFacet | None) -> bool:
        """Return whether this light source currently illuminates its scope."""
        if self.requires_switch or switchable is not None:
            return is_on
        return True


class ContainerFacet(HasAssets):
    """Asset holder policy for simple sandbox containers."""

    is_open: bool = True
    max_items: int | None = None
    accepts_traits: set[str] = Field(default_factory=set)
    allow_nested_containers: bool = False
    open_text: str = "Opened."
    close_text: str = "Closed."
    open_action_text: str = ""
    close_action_text: str = ""

    def can_open(self) -> bool:
        """Return whether this container can currently open."""
        return not self.is_open

    def open(self) -> None:
        """Mark this container open."""
        self.is_open = True

    def can_close(self) -> bool:
        """Return whether this container can currently close."""
        return self.is_open

    def close(self) -> None:
        """Mark this container closed."""
        self.is_open = False

    def can_accept_asset(self, asset: Token, *, current_count: int) -> bool:
        """Return whether this container policy accepts the asset."""
        if not self.is_open:
            return False
        if self.max_items is not None and current_count >= self.max_items:
            return False
        asset_traits = asset.traits
        if not self.allow_nested_containers and "container" in asset_traits:
            return False
        return not self.accepts_traits or bool(self.accepts_traits & asset_traits)

    def can_receive_asset(self, asset: Token, giver: HasAssets | None = None) -> bool:
        """Return whether this container can receive a discrete asset."""
        _ = giver
        return self.can_accept_asset(asset, current_count=len(self.assets))

    def can_give_asset(self, asset: Token, receiver: HasAssets | None = None) -> bool:
        """Return whether this container can release a discrete asset."""
        _ = receiver
        return self.is_open and self.has_asset(asset)
