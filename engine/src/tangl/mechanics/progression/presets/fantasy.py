from __future__ import annotations

from ..definition.canonical_slots import CanonicalSlot
from ..definition.stat_def import StatDef
from ..definition.stat_system import StatSystemDefinition
from ..dominance.patterns import CircularDominance
from .registry import register_preset

Fantasy3 = StatSystemDefinition(
    name="fantasy3",
    theme="fantasy",
    complexity=3,
    handler="probit",
    stats=[
        StatDef(
            name="body",
            description="Physical strength, health, and endurance",
            is_intrinsic=True,
            currency_name="stamina",
            canonical_slot=CanonicalSlot.PHYSICAL,
        ),
        StatDef(
            name="mind",
            description="Mental acuity, cleverness, and learning",
            is_intrinsic=True,
            currency_name="focus",
            canonical_slot=CanonicalSlot.MENTAL,
        ),
        StatDef(
            name="will",
            description="Spiritual resolve, courage, and magical potency",
            is_intrinsic=True,
            currency_name="resolve",
            canonical_slot=CanonicalSlot.SPIRITUAL,
        ),
    ],
    dominance_matrix={},
)

register_preset(Fantasy3)

Fantasy5 = StatSystemDefinition(
    name="fantasy5",
    theme="fantasy",
    complexity=5,
    handler="probit",
    stats=[
        StatDef(
            name="body",
            description="Physical strength, health, and endurance",
            is_intrinsic=True,
            currency_name="stamina",
            canonical_slot=CanonicalSlot.PHYSICAL,
        ),
        StatDef(
            name="mind",
            description="Mental acuity, cleverness, and learning",
            is_intrinsic=True,
            currency_name="focus",
            canonical_slot=CanonicalSlot.MENTAL,
        ),
        StatDef(
            name="will",
            description="Spiritual resolve, courage, and magical potency",
            is_intrinsic=True,
            currency_name="resolve",
            canonical_slot=CanonicalSlot.SPIRITUAL,
        ),
        StatDef(
            name="charm",
            description="Social grace, charisma, and influence",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.SOCIAL,
        ),
        StatDef(
            name="hidden",
            description="Stealth, guile, and covert action",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.COVERT,
        ),
    ],
    dominance_matrix=CircularDominance.generate(
        items=["body", "mind", "will", "charm", "hidden"],
        pattern={1: 1.0, 2: 0.5},
    ),
)

register_preset(Fantasy5)
