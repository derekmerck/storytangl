from __future__ import annotations

from tangl.mechanics.progression.challenges import StatChallenge, resolve_challenge
from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from tangl.mechanics.progression.entity.has_stats import HasStats
from tangl.mechanics.progression.entity.has_wallet import HasWallet
from tangl.mechanics.progression.growth import (
    DiminishingGrowthHandler,
    LinearGrowthHandler,
    SteppedGrowthHandler,
)


class Fighter(HasStats, HasWallet):
    """Test actor for challenge-driven growth."""


def _growth_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="growth",
        theme="test",
        complexity=2,
        handler="probit",
        stats=[
            StatDef(name="body", is_intrinsic=True, canonical_slot=CanonicalSlot.PHYSICAL),
            StatDef(name="sword", governed_by="body"),
        ],
    )


def _fighter(*, body: float = 12.0, sword: float = 10.0) -> Fighter:
    system = _growth_system()
    stats = HasStats.from_system(system, overrides={"body": body, "sword": sword}).stats
    return Fighter(stat_system=system, stats=stats, wallet={})


def test_growth_receipt_contains_primary_and_governor_deltas():
    fighter = _fighter()
    challenge = StatChallenge(domain="sword", difficulty="high")

    result = resolve_challenge(
        challenge,
        fighter,
        growth_handler=LinearGrowthHandler(),
        apply_growth=False,
        roll=0.6,
    )

    assert result.growth_receipt is not None
    assert result.growth_receipt.target_stat == "sword"
    assert "sword" in result.growth_receipt.applied_deltas
    assert "body" in result.growth_receipt.applied_deltas
    assert result.growth_receipt.applied is False


def test_growth_handlers_are_monotone_and_diminishing_is_smaller():
    fighter_linear = _fighter()
    fighter_step = _fighter()
    fighter_dim = _fighter()
    challenge = StatChallenge(domain="sword", difficulty="very high")

    linear = resolve_challenge(
        challenge,
        fighter_linear,
        growth_handler=LinearGrowthHandler(),
        apply_growth=False,
        roll=0.7,
    ).growth_receipt
    stepped = resolve_challenge(
        challenge,
        fighter_step,
        growth_handler=SteppedGrowthHandler(),
        apply_growth=False,
        roll=0.7,
    ).growth_receipt
    diminishing = resolve_challenge(
        challenge,
        fighter_dim,
        growth_handler=DiminishingGrowthHandler(),
        apply_growth=False,
        roll=0.7,
    ).growth_receipt

    assert linear is not None and stepped is not None and diminishing is not None
    assert linear.applied_deltas["sword"] >= stepped.applied_deltas["sword"]
    assert linear.applied_deltas["sword"] >= diminishing.applied_deltas["sword"]


def test_growth_disabled_does_not_mutate_entity():
    fighter = _fighter()
    baseline = fighter.sword.fv
    challenge = StatChallenge(domain="sword", difficulty="high")

    result = resolve_challenge(
        challenge,
        fighter,
        growth_handler=LinearGrowthHandler(),
        apply_growth=False,
        roll=0.6,
    )

    assert fighter.sword.fv == baseline
    assert result.growth_receipt is not None
    assert result.growth_receipt.applied is False


def test_growth_applies_when_enabled():
    fighter = _fighter()
    baseline_sword = fighter.sword.fv
    baseline_body = fighter.body.fv
    challenge = StatChallenge(domain="sword", difficulty="high")

    result = resolve_challenge(
        challenge,
        fighter,
        growth_handler=LinearGrowthHandler(),
        apply_growth=True,
        roll=0.6,
    )

    assert fighter.sword.fv > baseline_sword
    assert fighter.body.fv > baseline_body
    assert result.growth_receipt is not None
    assert result.growth_receipt.applied is True
