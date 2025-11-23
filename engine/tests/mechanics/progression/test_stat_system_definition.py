from __future__ import annotations

from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition


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
                currency_name="stamina",
                canonical_slot=CanonicalSlot.PHYSICAL,
            ),
            StatDef(
                name="mind",
                is_intrinsic=True,
                currency_name="focus",
                canonical_slot=CanonicalSlot.MENTAL,
            ),
            StatDef(
                name="sword",
                is_intrinsic=False,
                governed_by="body",
            ),
            StatDef(
                name="logic",
                is_intrinsic=False,
                governed_by="mind",
            ),
        ],
        dominance_matrix={
            "sword": {"logic": 1.0},
            "logic": {"sword": -1.0},
        },
        context_bonuses={
            "forest": {"sword": 0.5},
            "library": {"logic": 1.0},
        },
    )


def test_stat_system_views_and_maps():
    system = _example_system()

    assert system.name == "example"
    assert system.theme == "test"
    assert system.complexity == 4
    assert system.handler == "probit"

    assert system.stat_names == ["body", "mind", "sword", "logic"]

    intrinsic_names = [s.name for s in system.intrinsics]
    domain_names = [s.name for s in system.domains]

    assert intrinsic_names == ["body", "mind"]
    assert domain_names == ["sword", "logic"]

    assert set(system.currencies) == {"stamina", "focus"}
    assert system.intrinsic_map == {"sword": "body", "logic": "mind"}

    assert system.default_domain == "sword"


def test_stat_system_lookup_helpers():
    system = _example_system()

    assert system.get_stat("body") is not None
    assert system.get_stat("body").is_intrinsic  # type: ignore[union-attr]
    assert system.get_stat("missing") is None

    assert system.get_dominance("sword", "logic") == 1.0
    assert system.get_dominance("logic", "sword") == -1.0
    assert system.get_dominance("sword", "body") == 0.0

    assert system.get_context_bonus("forest", "sword") == 0.5
    assert system.get_context_bonus("library", "logic") == 1.0
    assert system.get_context_bonus("forest", "logic") == 0.0
    assert system.get_context_bonus("desert", "sword") == 0.0
