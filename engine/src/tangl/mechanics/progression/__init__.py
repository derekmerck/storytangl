from __future__ import annotations

from .definition.canonical_slots import CanonicalSlot
from .definition.stat_def import StatDef
from .definition.stat_system import StatSystemDefinition
from .dominance.patterns import CircularDominance
from .entity.has_stats import HasStats
from .entity.has_wallet import HasWallet
from .growth import (
    DiminishingGrowthHandler,
    GrowthHandler,
    GrowthReceipt,
    LinearGrowthHandler,
    SteppedGrowthHandler,
)
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
from .effects.donors import EffectDonor, TagDonor, gather_donor_effects, gather_donor_tags
from .presets.registry import all_presets, get_preset, register_preset
from .projection import (
    project_outcome_label,
    project_payout_label,
    project_payout_quality,
    project_quality,
    project_quality_label,
)
from .stats.stat import Stat
from .context.stat_context import StatContext
from .tasks import ResolutionSnapshot, Task, compute_delta, inspect_resolution, resolve_task
from .challenges import (
    ChallengePayout,
    ChallengeResult,
    StatChallenge,
    StatRequirement,
    resolve_challenge,
)

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
    "EffectDonor",
    "TagDonor",
    "gather_applicable_effects",
    "aggregate_modifiers",
    "gather_donor_effects",
    "gather_donor_tags",
    "register_preset",
    "get_preset",
    "all_presets",
    "Task",
    "ResolutionSnapshot",
    "resolve_task",
    "compute_delta",
    "inspect_resolution",
    "StatChallenge",
    "StatRequirement",
    "ChallengePayout",
    "ChallengeResult",
    "resolve_challenge",
    "project_quality",
    "project_quality_label",
    "project_outcome_label",
    "project_payout_quality",
    "project_payout_label",
    "GrowthHandler",
    "GrowthReceipt",
    "LinearGrowthHandler",
    "SteppedGrowthHandler",
    "DiminishingGrowthHandler",
]
