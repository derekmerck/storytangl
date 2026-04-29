"""Sandbox mechanics: dynamic scene-location hubs over normal choices."""

from .handlers import (
    advance_sandbox_time_on_wait,
    compose_sandbox_visibility_journal,
    contribute_sandbox_inventory_helpers,
    project_sandbox_asset_actions,
    project_sandbox_fixture_actions,
    project_sandbox_location_links,
    project_sandbox_scheduled_events,
    project_sandbox_unlocks,
    project_sandbox_wait,
)
from .location import (
    SandboxExit,
    SandboxLocation,
    SandboxLockable,
    normalize_sandbox_direction,
)
from .schedule import Schedule, ScheduleEntry, ScheduledEvent, ScheduledPresence
from .scope import SandboxInventory, SandboxScope
from .time import WorldTime, advance_world_turn, current_world_time, get_world_turn
from .visibility import SandboxProjectionState, SandboxVisibilityRule

__all__ = [
    "SandboxExit",
    "SandboxInventory",
    "SandboxLocation",
    "SandboxLockable",
    "SandboxProjectionState",
    "SandboxScope",
    "SandboxVisibilityRule",
    "Schedule",
    "ScheduleEntry",
    "ScheduledEvent",
    "ScheduledPresence",
    "WorldTime",
    "advance_sandbox_time_on_wait",
    "advance_world_turn",
    "compose_sandbox_visibility_journal",
    "contribute_sandbox_inventory_helpers",
    "current_world_time",
    "get_world_turn",
    "normalize_sandbox_direction",
    "project_sandbox_asset_actions",
    "project_sandbox_fixture_actions",
    "project_sandbox_location_links",
    "project_sandbox_scheduled_events",
    "project_sandbox_unlocks",
    "project_sandbox_wait",
]
