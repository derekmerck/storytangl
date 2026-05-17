"""World-local domain types for *Coronate the Regent*.

The protagonist is a :class:`Regent`: the story-layer :class:`Player` fixture
composed with the progression mechanics' :class:`HasStats` and :class:`HasWallet`
mixins. The stat system below is intentionally a small *seed*: more intrinsics,
domains, and currencies are meant to be added as plain data (extra ``StatDef``
entries) rather than as code, so scaling complexity stays a configuration
concern.
"""

from __future__ import annotations

from typing import ClassVar, Dict

from pydantic import Field

from tangl.mechanics.progression import Outcome, SituationalEffect

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

    # Mood biases *which* training pays off this week: a growth_modifier
    # scoped to the skill-category tag a TrainBlock stamps on its challenge.
    MOOD_EFFECTS: ClassVar[dict[str, list[SituationalEffect]]] = {
        "martial": [
            SituationalEffect(
                name="martial mood",
                applies_to_tags=frozenset({"#martial"}),
                growth_modifier=1.0,
            ),
            SituationalEffect(
                name="martial mood (courtly slump)",
                applies_to_tags=frozenset({"#courtly"}),
                growth_modifier=-0.5,
            ),
        ],
        "studious": [
            SituationalEffect(
                name="studious mood",
                applies_to_tags=frozenset({"#courtly"}),
                growth_modifier=1.0,
            ),
        ],
    }
    # The dragonslayer sword guarantees the kill: a forced_outcome override
    # on the #dragon-tagged check, so survival is decided by the mechanics
    # (no authored guard crutch on the branch).
    SWORD_EFFECT: ClassVar[SituationalEffect] = SituationalEffect(
        name="dragonslayer sword",
        applies_to_tags=frozenset({"#dragon"}),
        forced_outcome=Outcome.MAJOR_SUCCESS,
    )

    def get_situational_effects(self) -> list[SituationalEffect]:
        effects: list[SituationalEffect] = []
        if self.mood:
            effects.extend(self.MOOD_EFFECTS.get(self.mood, ()))
        if self.has("dragonslayer_sword"):
            effects.append(self.SWORD_EFFECT)
        return effects

    def get_context_tags(self) -> set[str]:
        # Challenges carry their own category/scenario tags; the protagonist
        # contributes none of its own today.
        return set()


Regent.model_rebuild()


# --- Story-facing blocks ----------------------------------------------------

from uuid import UUID  # noqa: E402

from tangl.core import Selector  # noqa: E402
from tangl.mechanics.progression import (  # noqa: E402
    HasStatChallenge,
    HasTraining,
    LinearGrowthHandler,
)
from tangl.mechanics.progression.challenges import StatChallenge  # noqa: E402
from tangl.story import Block  # noqa: E402
from tangl.vm import on_update  # noqa: E402


def _regent(graph) -> Regent | None:
    found = graph.find_one(Selector(has_kind=Regent)) if graph is not None else None
    return found if isinstance(found, Regent) else None


class TrainCombat(HasTraining, Block):
    _training_skill = "combat"
    _training_difficulty = "ok"
    _training_tags = frozenset({"training", "#martial"})
    _growth_handler = LinearGrowthHandler()


class TrainCharm(HasTraining, Block):
    _training_skill = "charm"
    _training_difficulty = "ok"
    _training_tags = frozenset({"training", "#courtly"})
    _growth_handler = LinearGrowthHandler()


class PrinceAudience(HasStatChallenge, Block):
    # Difficulty 0.0: a base Regent's competency (~10) yields p_success ~1.0,
    # so the check passes deterministically. The demo's branching turns on the
    # *choice* to attend the prince, not on a stat coin-flip.
    _challenge = StatChallenge(
        name="The prince's visit", domain="charm", difficulty=0.0
    )


class DragonFight(HasStatChallenge, Block):
    # Lethal by design: base combat fails this deterministically, so survival
    # depends on the dragonslayer sword (an inter-phase payoff), not the roll.
    _challenge = StatChallenge(
        name="The dragon", domain="combat", difficulty=20.0, tags={"#dragon"}
    )


class GrantBlock(Block):
    """Deterministically grant flags/inventory (and pay an optional cost).

    A small world-local state-mutation primitive used to set storyline flags
    and hand over items, keyed off the protagonist found in the graph.
    """

    _grant_flags: ClassVar[tuple[str, ...]] = ()
    _grant_inv: ClassVar[tuple[str, ...]] = ()
    _grant_cost: ClassVar[dict[str, int]] = {}


class GrantImpressedPrince(GrantBlock):
    _grant_flags = ("impressed_prince",)


class GrantIrritatedDragon(GrantBlock):
    _grant_flags = ("irritated_dragon",)


class BuySword(GrantBlock):
    _grant_inv = ("dragonslayer_sword",)
    _grant_cost = {"coin": 3}


@on_update(wants_caller_kind=GrantBlock, wants_exact_kind=False)
def apply_grant(cursor=None, *, caller=None, ctx, **_kw):
    block = cursor if isinstance(cursor, GrantBlock) else caller
    if not isinstance(block, GrantBlock):
        return None
    regent = _regent(getattr(block, "graph", None))
    if regent is None:
        return None
    cost = dict(block._grant_cost)
    if cost:
        if not regent.can_afford(cost):
            return None
        regent.spend(cost)
    for flag in block._grant_flags:
        regent.flags.add(flag)
    for item in block._grant_inv:
        regent.inv.add(item)
    return None


for _cls in (
    TrainCombat,
    TrainCharm,
    PrinceAudience,
    DragonFight,
    GrantBlock,
    GrantImpressedPrince,
    GrantIrritatedDragon,
    BuySword,
):
    _cls.model_rebuild(_types_namespace={"UUID": UUID})
