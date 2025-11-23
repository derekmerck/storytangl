from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from ..handlers.base import StatHandler
from ..handlers.probit import ProbitStatHandler
from .situational import SituationalEffect


@dataclass(frozen=True)
class ModifierTotals:
    """
    Aggregate modifiers for a single stat in a single scenario.

    Attributes
    ----------
    difficulty:
        Sum of difficulty modifiers (before clamping).
    competency:
        Sum of competency modifiers (before clamping).
    clamped_difficulty:
        Difficulty modifier after handler-specific clamping.
    clamped_competency:
        Competency modifier after handler-specific clamping.
    active_effects:
        The list of effects that contributed to these totals.
    """

    difficulty: float
    competency: float
    clamped_difficulty: float
    clamped_competency: float
    active_effects: List[SituationalEffect]


def gather_applicable_effects(
    effects: Iterable[SituationalEffect],
    *,
    tags: Iterable[str] | None = None,
    stat_name: str | None = None,
) -> List[SituationalEffect]:
    """
    Filter a collection of effects for those that apply to this
    scenario (tags + stat).

    This is a pure helper to keep the logic testable and re-usable.
    """
    return [
        eff
        for eff in effects
        if eff.applies(tags=tags, stat_name=stat_name)
    ]


def aggregate_modifiers(
    effects: Iterable[SituationalEffect],
    *,
    tags: Iterable[str] | None = None,
    stat_name: str | None = None,
    handler: type[StatHandler] = ProbitStatHandler,
) -> ModifierTotals:
    """
    Aggregate and clamp situational modifiers for a given stat.

    Parameters
    ----------
    effects:
        All candidate effects in scope.
    tags:
        Scenario tags, e.g. {"#combat", "#night"}.
    stat_name:
        Name of the stat being tested (e.g., "body").
    handler:
        StatHandler whose clamp rules (MODIFIER_CLAMP) will be used.

    Returns
    -------
    ModifierTotals
        Summed and clamped modifiers plus the active effects.
    """
    applicable: List[SituationalEffect] = gather_applicable_effects(
        effects,
        tags=tags,
        stat_name=stat_name,
    )

    total_difficulty = sum(e.difficulty_modifier for e in applicable)
    total_competency = sum(e.competency_modifier for e in applicable)

    clamped_diff = handler.clamp_modifiers(total_difficulty)
    clamped_comp = handler.clamp_modifiers(total_competency)

    return ModifierTotals(
        difficulty=total_difficulty,
        competency=total_competency,
        clamped_difficulty=clamped_diff,
        clamped_competency=clamped_comp,
        active_effects=applicable,
    )
