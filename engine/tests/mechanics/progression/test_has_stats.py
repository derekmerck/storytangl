from __future__ import annotations

from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from tangl.mechanics.progression.entity.has_stats import HasStats
from tangl.mechanics.progression.measures import Quality
from tangl.mechanics.progression.stats.stat import Stat


def _example_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="example",
        theme="test",
        complexity=4,
        handler="probit",
        stats=[
            StatDef(
                name="body",
                is_intrinsic=True,
                description="Physical power",
                canonical_slot=CanonicalSlot.PHYSICAL,
            ),
            StatDef(
                name="mind",
                is_intrinsic=True,
                description="Mental acuity",
                canonical_slot=CanonicalSlot.MENTAL,
            ),
            StatDef(
                name="sword",
                governed_by="body",
                description="Swordfighting skill",
            ),
            StatDef(
                name="logic",
                governed_by="mind",
                description="Reasoning and puzzles",
            ),
        ],
    )


def test_from_system_populates_all_stats_with_defaults():
    system = _example_system()
    entity = HasStats.from_system(system)

    assert set(entity.stats.keys()) == {"body", "mind", "sword", "logic"}

    for stat in entity.stats.values():
        assert isinstance(stat, Stat)
        assert abs(stat.fv - 10.0) < 1e-6
        assert stat.quality is Quality.MID


def test_from_system_with_overrides():
    system = _example_system()
    entity = HasStats.from_system(
        system,
        base_fv=10.0,
        overrides={"body": 14.0, "sword": "high"},
    )

    assert abs(entity.body.fv - 14.0) < 1e-6
    assert entity.sword.quality is Quality.HIGH


def test_get_set_stat_and_iter_stats():
    system = _example_system()
    entity = HasStats.from_system(system)

    body = entity.get_stat("body")
    assert isinstance(body, Stat)

    entity.set_stat("body", 16.0)
    entity.set_stat("logic", 5)
    assert entity.body.fv > 10.0
    assert entity.logic.qv == 5

    subset = dict(entity.iter_stats(["body", "sword"]))
    assert set(subset.keys()) == {"body", "sword"}


def test_compute_competency_rules():
    system = _example_system()
    entity = HasStats.from_system(
        system,
        overrides={
            "body": 14.0,
            "mind": 8.0,
            "sword": 12.0,
            "logic": 10.0,
        },
    )

    assert abs(entity.compute_competency("body") - 14.0) < 1e-6
    assert abs(entity.compute_competency("mind") - 8.0) < 1e-6

    assert abs(entity.compute_competency("sword") - 13.0) < 1e-6
    assert abs(entity.compute_competency("logic") - 9.0) < 1e-6

    assert abs(entity.compute_competency("missing") - 10.0) < 1e-6
    assert abs(entity.compute_competency(None) - 11.0) < 1e-6


def test_dynamic_attribute_access_and_missing():
    system = _example_system()
    entity = HasStats.from_system(system)

    assert isinstance(entity.body, Stat)

    try:
        _ = entity.hp  # type: ignore[attr-defined]
    except AttributeError:
        pass
    else:
        raise AssertionError("Expected AttributeError for unknown attribute")
