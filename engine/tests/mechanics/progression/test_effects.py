from __future__ import annotations

from mechanics.progression.effects import (
    SituationalEffect,
    aggregate_modifiers,
    gather_applicable_effects,
)
from mechanics.progression.handlers.linear import LinearStatHandler
from mechanics.progression.handlers.probit import ProbitStatHandler


def test_situational_effect_basic_matching_on_tags_and_stats():
    sword = SituationalEffect(
        name="Sword of Kings",
        applies_to_tags={"#combat"},
        applies_to_stats={"body"},
        difficulty_modifier=-0.5,
    )
    arena_crowd = SituationalEffect(
        name="Cheering Crowd",
        applies_to_tags={"#arena"},
        competency_modifier=1.0,
    )
    generic_fatigue = SituationalEffect(
        name="Fatigue",
        applies_to_tags=frozenset(),  # always eligible by tags
        applies_to_stats=frozenset(),  # all stats
        difficulty_modifier=0.5,
    )

    effects = [sword, arena_crowd, generic_fatigue]

    # Scenario: combat in arena, testing "body"
    tags = {"#combat", "#arena"}

    applicable_body = gather_applicable_effects(
        effects,
        tags=tags,
        stat_name="body",
    )
    names_body = {e.name for e in applicable_body}
    assert names_body == {"Sword of Kings", "Cheering Crowd", "Fatigue"}

    # Scenario: combat in arena, testing "mind"
    applicable_mind = gather_applicable_effects(
        effects,
        tags=tags,
        stat_name="mind",
    )
    names_mind = {e.name for e in applicable_mind}
    # sword is bound to body, so it should not apply to mind
    assert names_mind == {"Cheering Crowd", "Fatigue"}

    # Scenario: a non-combat test
    noncombat_tags = {"#audition"}
    applicable_body_noncombat = gather_applicable_effects(
        effects,
        tags=noncombat_tags,
        stat_name="body",
    )
    # Only generic_fatigue applies; Sword (needs #combat), Crowd (needs #arena)
    assert {e.name for e in applicable_body_noncombat} == {"Fatigue"}


def test_aggregate_modifiers_sum_and_clamp_with_probit():
    # Many small bonuses to force clamping
    effects = [
        SituationalEffect(
            name=f"Bonus {i}",
            applies_to_tags=frozenset({"#combat"}),
            applies_to_stats=frozenset({"body"}),
            competency_modifier=0.7,
        )
        for i in range(10)
    ]

    tags = {"#combat"}
    totals = aggregate_modifiers(
        effects,
        tags=tags,
        stat_name="body",
        handler=ProbitStatHandler,
    )

    # Raw total is 10 * 0.7 = 7.0
    assert abs(totals.competency - 7.0) < 1e-6

    # But clamp should be ±MODIFIER_CLAMP = ±2.5 by default
    assert totals.clamped_competency == ProbitStatHandler.MODIFIER_CLAMP

    # No difficulty modifiers
    assert totals.difficulty == 0.0
    assert totals.clamped_difficulty == 0.0

    # All effects should be active
    assert len(totals.active_effects) == 10


def test_aggregate_modifiers_respects_handler_specific_clamp():
    # Use a different handler with a tighter clamp to show it works
    class TinyClampHandler(LinearStatHandler):
        MODIFIER_CLAMP = 1.0

    effects = [
        SituationalEffect(
            name="Big Buff",
            competency_modifier=5.0,
        ),
    ]

    totals = aggregate_modifiers(
        effects,
        tags={"#anything"},
        stat_name="body",
        handler=TinyClampHandler,
    )

    assert totals.competency == 5.0
    assert totals.clamped_competency == 1.0  # tiny clamp applied
