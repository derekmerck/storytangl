"""World-local domain types for *Coronate the Regent*.

The protagonist is a :class:`Regent`: the story-layer :class:`Player` fixture
composed with the progression mechanics' :class:`HasStats` and :class:`HasWallet`
mixins. The stat system below is intentionally a small *seed*: more intrinsics,
domains, and currencies are meant to be added as plain data (extra ``StatDef``
entries) rather than as code, so scaling complexity stays a configuration
concern.
"""

from __future__ import annotations

from typing import Dict

from pydantic import Field

from tangl.mechanics.progression.definition.canonical_slots import CanonicalSlot
from tangl.mechanics.progression.definition.stat_def import StatDef
from tangl.mechanics.progression.definition.stat_system import StatSystemDefinition
from tangl.mechanics.progression.entity.has_stats import HasStats
from tangl.mechanics.progression.entity.has_wallet import HasWallet
from tangl.mechanics.progression.stats.stat import Stat
from tangl.story import Player


# --- Seed stat system (extend by adding StatDef data, not code) -------------

CORONATE_STATS = StatSystemDefinition(
    name="coronate_the_regent",
    theme="court",
    complexity=2,
    handler="probit",
    stats=[
        StatDef(name="body", description="Vigor and physical resilience.",
                is_intrinsic=True, currency_name="stamina",
                canonical_slot=CanonicalSlot.PHYSICAL),
        StatDef(name="mind", description="Learning, planning, and arcane sense.",
                is_intrinsic=True, canonical_slot=CanonicalSlot.MENTAL),
        StatDef(name="spirit", description="Composure, charm, and bearing.",
                is_intrinsic=True, currency_name="coin",
                canonical_slot=CanonicalSlot.SPIRITUAL),
        StatDef(name="combat", description="Martial skill.",
                governed_by="body", canonical_slot=CanonicalSlot.PHYSICAL),
        StatDef(name="magic", description="Trained arcane practice.",
                governed_by="mind", canonical_slot=CanonicalSlot.SPIRITUAL),
        StatDef(name="charm", description="Courtly persuasion.",
                governed_by="spirit", canonical_slot=CanonicalSlot.SOCIAL),
    ],
    dominance_matrix={},
)


def _default_stats() -> Dict[str, Stat]:
    """Build the starting stat block from the seed system (reuse, not parallel)."""
    return HasStats.from_system(CORONATE_STATS, base_fv=10.0).stats


class Regent(Player, HasStats, HasWallet):
    """Protagonist of *Coronate the Regent*.

    Composes the story-layer :class:`Player` namespace fixture with progression
    stats and a currency wallet. Constructible with no arguments so it can be
    materialized and round-tripped like any other graph node; pass overrides to
    customize a playthrough.
    """

    stat_system: StatSystemDefinition = CORONATE_STATS
    # Overriding these fields replaces the mixin FieldInfo, so the snapshot
    # `include` marker is re-declared here alongside the seed defaults.
    stats: Dict[str, Stat] = Field(
        default_factory=_default_stats, json_schema_extra={"include": True}
    )
    wallet: Dict[str, int] = Field(
        default_factory=lambda: {"coin": 3, "stamina": 5},
        json_schema_extra={"include": True},
    )


Regent.model_rebuild()
