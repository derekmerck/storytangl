from __future__ import annotations

from tangl.mechanics.progression.context.stat_context import StatContext
from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from tangl.mechanics.progression.measures import Quality


def _simple_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="simple",
        theme="test",
        complexity=2,
        handler="probit",
        stats=[
            StatDef(
                name="body",
                is_intrinsic=True,
                canonical_slot=CanonicalSlot.PHYSICAL,
            ),
            StatDef(
                name="mind",
                is_intrinsic=True,
                canonical_slot=CanonicalSlot.MENTAL,
            ),
        ],
    )


def test_stat_context_make_stats_with_defaults_and_overrides():
    system = _simple_system()
    ctx = StatContext(stat_system=system)

    stats = ctx.make_stats(base_fv=10.0)
    assert set(stats.keys()) == {"body", "mind"}
    assert stats["body"].quality is Quality.MID
    assert stats["mind"].quality is Quality.MID

    stats2 = ctx.make_stats(
        base_fv=10.0,
        overrides={"body": "high"},
    )
    assert stats2["body"].quality is Quality.HIGH
    assert stats2["mind"].quality is Quality.MID
