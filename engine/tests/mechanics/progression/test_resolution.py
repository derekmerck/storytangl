from __future__ import annotations

import pytest

from mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from mechanics.progression.entity.has_stats import HasStats
from mechanics.progression.entity.has_wallet import HasWallet
from mechanics.progression.effects import SituationalEffect
from mechanics.progression.outcomes import Outcome
from mechanics.progression.tasks.resolution import compute_delta, resolve_task
from mechanics.progression.tasks.task import Task


def _combat_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="combat",
        theme="test",
        complexity=4,
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
            StatDef(
                name="sword",
                governed_by="body",
            ),
            StatDef(
                name="logic",
                governed_by="mind",
            ),
        ],
        # simple dominance: sword > logic
        dominance_matrix={
            "sword": {"logic": 1.0},
            "logic": {"sword": -1.0},
        },
        context_bonuses={
            "forest": {"sword": 0.5},
            "library": {"logic": 0.5},
        },
    )


def _fighter_and_mage(system: StatSystemDefinition):
    fighter = HasStats.from_system(
        system,
        overrides={
            "body": 14.0,
            "mind": 8.0,
            "sword": 12.0,
            "logic": 9.0,
        },
    )
    mage = HasStats.from_system(
        system,
        overrides={
            "body": 8.0,
            "mind": 14.0,
            "sword": 9.0,
            "logic": 12.0,
        },
    )
    return fighter, mage


def test_compute_delta_monotone_with_effects_and_dominance():
    system = _combat_system()
    fighter, mage = _fighter_and_mage(system)

    # base sword task
    task = Task(
        name="Sword clash",
        domain="sword",
        difficulty={"sword": 12.0},
        tags={"#combat"},
    )

    # No effects, neutral context, no explicit dominance
    delta_base = compute_delta(
        task,
        fighter,
        system=system,
        effects=[],
        context_tags=set(),
    )
    # fighter: body=14, sword=12 → competency ~ (14+12)/2 = 13
    # difficulty = 12 → delta ≈ 1
    assert 0.5 < delta_base < 2.0

    # Add positive effects and dominance: should increase delta
    sword_buff = SituationalEffect(
        name="Sword blessing",
        applies_to_tags={"#combat"},
        applies_to_stats={"sword"},
        competency_modifier=1.0,
    )
    forest_edge = "forest"  # context bonus +0.5 to sword
    delta_buffed = compute_delta(
        task,
        fighter,
        system=system,
        effects=[sword_buff],
        context_tags={forest_edge},
        dominance_attacker_domain="sword",
        dominance_defender_domain="logic",
    )

    assert delta_buffed > delta_base


def test_resolve_task_outcome_distribution_with_fixed_roll():
    system = _combat_system()
    fighter, mage = _fighter_and_mage(system)

    # Fighter sword task vs moderate difficulty
    task_easy = Task(
        name="Easy sword test",
        domain="sword",
        difficulty={"sword": 10.0},
        tags={"#combat"},
    )

    # Hard version of same task
    task_hard = Task(
        name="Hard sword test",
        domain="sword",
        difficulty={"sword": 16.0},
        tags={"#combat"},
    )

    # Fixed roll: success probability should drive outcome ordering
    roll = 0.5

    outcome_easy = resolve_task(
        task_easy,
        fighter,
        system=system,
        effects=[],
        context_tags=set(),
        roll=roll,
    )
    outcome_hard = resolve_task(
        task_hard,
        fighter,
        system=system,
        effects=[],
        context_tags=set(),
        roll=roll,
    )

    # Easier task should not produce a worse outcome than the harder one.
    assert outcome_easy.value >= outcome_hard.value

@pytest.mark.skip("Re-enable when HasWallet in asset is working/tested")
def test_resolve_task_with_wallet_integration():
    system = _combat_system()
    fighter, _ = _fighter_and_mage(system)

    # Simple wallet wrapper: use actual HasWallet to match protocol
    wallet = HasWallet.from_system(
        system,
        base_amount=0,
        overrides={"stamina": 5},
    )

    task = Task(
        name="Stamina taxing move",
        domain="body",
        difficulty={"body": 12.0},
        cost={"stamina": 3},
        reward={"stamina": 1},
        tags={"#combat"},
    )

    # Before: 5 stamina
    assert wallet.wallet["stamina"] == 5

    # Resolve with auto_spend/auto_reward and fixed roll
    outcome = resolve_task(
        task,
        fighter,
        system=system,
        wallet=wallet,
        roll=0.5,
    )

    assert isinstance(outcome, Outcome)
    # After: spent 3, earned 1 → 3 stamina
    assert wallet.wallet["stamina"] == 3

    # Unaffordable cost should raise
    expensive_task = Task(
        name="Too exhausting move",
        domain="body",
        difficulty={"body": 12.0},
        cost={"stamina": 100},
    )
    try:
        resolve_task(
            expensive_task,
            fighter,
            system=system,
            wallet=wallet,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unaffordable task cost")
