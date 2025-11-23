from __future__ import annotations

from ..definition.canonical_slots import CanonicalSlot
from ..definition.stat_def import StatDef
from ..definition.stat_system import StatSystemDefinition
from ..dominance.patterns import CircularDominance
from .registry import register_preset

Cyberpunk5 = StatSystemDefinition(
    name="cyberpunk5",
    theme="cyberpunk",
    complexity=5,
    handler="probit",
    stats=[
        StatDef(
            name="meat",
            description="Raw physical capability in the real world",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.PHYSICAL,
        ),
        StatDef(
            name="chrome",
            description="Quality and integration of cybernetic augments",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.PHYSICAL,
        ),
        StatDef(
            name="net",
            description="Skill and presence in virtual space",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.MENTAL,
        ),
        StatDef(
            name="street",
            description="Social capital and reputation",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.SOCIAL,
        ),
        StatDef(
            name="shadow",
            description="Stealth, subterfuge, and deniability",
            is_intrinsic=True,
            canonical_slot=CanonicalSlot.COVERT,
        ),
    ],
    dominance_matrix=CircularDominance.generate(
        items=["meat", "chrome", "net", "street", "shadow"],
        pattern={1: 0.75},
    ),
)

register_preset(Cyberpunk5)
