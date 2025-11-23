from __future__ import annotations

from .definition.canonical_slots import CanonicalSlot
from .definition.stat_def import StatDef
from .definition.stat_system import StatSystemDefinition
from .dominance.patterns import CircularDominance
from .entity.has_stats import HasStats
from .entity.has_wallet import HasWallet
from .handlers.base import StatHandler
from .handlers.linear import LinearStatHandler
from .handlers.logint import LogIntStatHandler
from .handlers.probit import ProbitStatHandler
from .measures import Quality
from .outcomes import Outcome, sample_outcome
from .effects import (
    SituationalEffect,
    aggregate_modifiers,
    gather_applicable_effects,
)
from .presets.registry import all_presets, get_preset, register_preset
from .stats.stat import Stat
from .context.stat_context import StatContext
from .tasks import Task, compute_delta, resolve_task

__all__ = [
    "Quality",
    "Outcome",
    "sample_outcome",
    "Stat",
    "StatHandler",
    "ProbitStatHandler",
    "LinearStatHandler",
    "LogIntStatHandler",
    "StatDef",
    "StatSystemDefinition",
    "CanonicalSlot",
    "CircularDominance",
    "HasStats",
    "HasWallet",
    "StatContext",
    "SituationalEffect",
    "gather_applicable_effects",
    "aggregate_modifiers",
    "register_preset",
    "get_preset",
    "all_presets",
    "Task",
    "resolve_task",
    "compute_delta",
]
