"""Shared scope facade for sandbox locations."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core import contribute_ns
from tangl.story.concepts.asset import HasAssets
from tangl.vm import TraversableNode

from .mob import SandboxMob
from .schedule import ScheduledEvent, ScheduledPresence
from .visibility import SandboxVisibilityRule


class SandboxInventory(HasAssets):
    """Lightweight ready-at-hand asset holder for sandbox player inventory."""


class SandboxScope(TraversableNode):
    """Chapter-like ancestor that donates sandbox rules to child locations."""

    scheduled_events: list[ScheduledEvent] = Field(default_factory=list)
    scheduled_presence: list[ScheduledPresence] = Field(default_factory=list)
    mobs: list[SandboxMob] = Field(default_factory=list)
    visibility_rules: list[SandboxVisibilityRule] = Field(default_factory=list)
    player_assets: SandboxInventory = Field(default_factory=SandboxInventory)
    wait_enabled: bool | None = True
    wait_text: str | None = "Wait"
    wait_turn_delta: int | None = 1

    @contribute_ns
    def provide_sandbox_scope_symbols(self) -> dict[str, Any]:
        """Publish scope metadata to descendant namespaces."""
        return {
            "sandbox_scope": self.get_label(),
            "sandbox_scope_node": self,
            "sandbox_mobs": {mob.get_label(): mob for mob in self.mobs},
            "player_assets": self.player_assets,
            "player_inv": self.player_assets.assets,
        }
