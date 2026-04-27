"""World-time helpers for sandbox-style dynamic hubs."""

from __future__ import annotations

from typing import Any, Protocol

from tangl.core.bases import BaseModelPlus


class HasMutableLocals(Protocol):
    """Object exposing mutable local state."""

    locals: dict[str, Any] | None


class HasWorldTurnScope(HasMutableLocals, Protocol):
    """Object whose ancestry can contain scoped world time."""

    ancestors: list["HasWorldTurnScope"]


class WorldTime(BaseModelPlus):
    """Derived calendar view over a monotonically increasing world turn."""

    turn: int = 0
    period: int = 1
    day: int = 1
    day_of_month: int = 1
    month: int = 1
    season: int = 1
    year: int = 1

    @classmethod
    def from_turn(
        cls,
        turn: int,
        *,
        periods_per_day: int = 4,
        days_per_week: int = 7,
        days_per_month: int = 28,
        months_per_year: int = 12,
        months_per_season: int = 3,
    ) -> "WorldTime":
        """Build a deterministic calendar view from a zero-based turn count."""
        if turn < 0:
            raise ValueError("turn must be non-negative")
        if periods_per_day <= 0:
            raise ValueError("periods_per_day must be positive")
        if days_per_week <= 0:
            raise ValueError("days_per_week must be positive")
        if days_per_month <= 0:
            raise ValueError("days_per_month must be positive")
        if months_per_year <= 0:
            raise ValueError("months_per_year must be positive")
        if months_per_season <= 0:
            raise ValueError("months_per_season must be positive")

        day_index = turn // periods_per_day
        month_index = day_index // days_per_month
        month = (month_index % months_per_year) + 1
        return cls(
            turn=turn,
            period=(turn % periods_per_day) + 1,
            day=(day_index % days_per_week) + 1,
            day_of_month=(day_index % days_per_month) + 1,
            month=month,
            season=((month - 1) // months_per_season) + 1,
            year=(month_index // months_per_year) + 1,
        )


def get_world_turn(source: HasWorldTurnScope) -> int:
    """Return the nearest scoped ``world_turn`` as an integer, defaulting to zero."""
    locals_ = source.locals
    if isinstance(locals_, dict) and "world_turn" in locals_:
        return int(locals_["world_turn"])
    for candidate in source.ancestors:
        locals_ = candidate.locals
        if isinstance(locals_, dict) and "world_turn" in locals_:
            return int(locals_["world_turn"])
    return 0


def current_world_time(source: HasWorldTurnScope) -> WorldTime:
    """Return the current derived `WorldTime` for a graph or node-like object."""
    return WorldTime.from_turn(get_world_turn(source))


def advance_world_turn(source: HasMutableLocals, delta: int = 1) -> int:
    """Increment ``source.locals['world_turn']`` and return the updated value."""
    if delta < 0:
        raise ValueError("delta must be non-negative")
    locals_ = source.locals
    if not isinstance(locals_, dict):
        raise TypeError("source must expose a mutable locals dict")
    next_turn = int(locals_.get("world_turn", 0)) + delta
    locals_["world_turn"] = next_turn
    return next_turn
