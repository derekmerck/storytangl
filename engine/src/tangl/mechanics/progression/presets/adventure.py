from __future__ import annotations

from ..definition.canonical_slots import CanonicalSlot
from ..definition.stat_def import StatDef
from ..definition.stat_system import StatSystemDefinition
from .registry import register_preset

Adventure2 = StatSystemDefinition(
    name="adventure2",
    theme="adventure",
    complexity=2,
    handler="probit",
    stats=[
        StatDef(
            name="strength",
            description="Raw physical power, toughness, and fighting grit",
            is_intrinsic=True,
            currency_name="stamina",
            canonical_slot=CanonicalSlot.PHYSICAL,
        ),
        StatDef(
            name="magic",
            description="Arcane potency, control, and mystical sensitivity",
            is_intrinsic=True,
            currency_name="mana",
            canonical_slot=CanonicalSlot.SPIRITUAL,
        ),
    ],
    dominance_matrix={},
)

register_preset(Adventure2)
