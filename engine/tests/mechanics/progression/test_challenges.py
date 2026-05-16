from __future__ import annotations

import pytest

from tangl.mechanics.progression.challenges import (
    ChallengePayout,
    StatChallenge,
    resolve_challenge,
)
from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from tangl.mechanics.progression.effects import SituationalEffect
from tangl.mechanics.progression.entity.has_stats import HasStats
from tangl.mechanics.progression.entity.has_wallet import HasWallet
from tangl.mechanics.progression.measures import Quality
from tangl.mechanics.progression.outcomes import Outcome
from tangl.mechanics.progression.presets import adventure  # noqa: F401
from tangl.mechanics.progression.presets.registry import get_preset
from tangl.mechanics.progression.projection import project_payout_quality, project_quality
from tangl.mechanics.progression.stats.stat import Stat


class Adventurer(HasStats, HasWallet):
    """Test actor with both stats and a wallet."""


class SimpleEffectDonor:
    def __init__(self, *effects: SituationalEffect):
        self.effects = list(effects)

    def get_situational_effects(self):
        return list(self.effects)


class SimpleTagDonor:
    def __init__(self, *tags: str):
        self.tags = set(tags)

    def get_context_tags(self):
        return set(self.tags)


def _adventure_actor(
    *,
    strength: float = 13.0,
    magic: float = 9.0,
    stamina: int = 5,
    mana: int = 2,
) -> Adventurer:
    system = get_preset("adventure2")
    stats = HasStats.from_system(
        system,
        overrides={"strength": strength, "magic": magic},
    ).stats
    wallet = HasWallet.from_system(
        system,
        overrides={"stamina": stamina, "mana": mana},
    ).wallet
    return Adventurer(stat_system=system, stats=stats, wallet=wallet)


def _social_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="social",
        theme="test",
        complexity=2,
        handler="probit",
        stats=[
            StatDef(name="strength", is_intrinsic=True, canonical_slot=CanonicalSlot.PHYSICAL),
            StatDef(name="magic", is_intrinsic=True, canonical_slot=CanonicalSlot.SPIRITUAL),
            StatDef(name="wealth", is_intrinsic=True, canonical_slot=CanonicalSlot.SOCIAL),
        ],
    )


def test_challenge_normalizes_quality_like_difficulty_inputs():
    system = get_preset("adventure2")
    challenge_quality = StatChallenge(domain="strength", difficulty=Quality.HIGH)
    challenge_tier = StatChallenge(domain="strength", difficulty=4)
    challenge_name = StatChallenge(domain="strength", difficulty="high")

    handler = Stat(10).handler
    quality_difficulty = challenge_quality.normalized_difficulty(
        handler=handler,
        domain=system.default_domain,
    )
    tier_difficulty = challenge_tier.normalized_difficulty(
        handler=handler,
        domain=system.default_domain,
    )
    name_difficulty = challenge_name.normalized_difficulty(
        handler=handler,
        domain=system.default_domain,
    )

    assert quality_difficulty == tier_difficulty == name_difficulty


def test_challenge_to_task_honors_empty_overrides():
    challenge = StatChallenge(
        domain="strength",
        difficulty="high",
        cost={"stamina": 2},
        tags={"#combat"},
    )

    task = challenge.to_task(
        handler=Stat.handler,
        difficulty={"magic": 8.0},
        cost={},
        tags=set(),
    )

    assert task.difficulty == {"magic": 8.0}
    assert task.cost == {}
    assert task.tags == set()


def test_resolve_challenge_outcome_is_monotone_for_fixed_roll():
    actor = _adventure_actor()
    easy = StatChallenge(domain="strength", difficulty="poor")
    hard = StatChallenge(domain="strength", difficulty="very high")

    easy_result = resolve_challenge(easy, actor, roll=0.5)
    hard_result = resolve_challenge(hard, actor, roll=0.5)

    assert easy_result.success_likelihood >= hard_result.success_likelihood
    assert easy_result.outcome.value >= hard_result.outcome.value


def test_resolve_challenge_spends_cost_and_grants_payout():
    actor = _adventure_actor()
    challenge = StatChallenge(
        name="Smash warded door",
        domain="strength",
        difficulty="poor",
        cost={"stamina": 2},
        payout=ChallengePayout(
            by_outcome={
                Outcome.SUCCESS: {"mana": 1},
                Outcome.MAJOR_SUCCESS: {"mana": 2},
            }
        ),
    )

    result = resolve_challenge(challenge, actor, wallet=actor, roll=0.1)

    assert result.cost_paid == {"stamina": 2}
    assert result.payout_granted == {"mana": 2}
    assert actor.wallet["stamina"] == 3
    assert actor.wallet["mana"] == 4


def test_challenge_result_exposes_projection_labels():
    actor = _adventure_actor()
    challenge = StatChallenge(
        name="Lift the portcullis",
        domain="strength",
        difficulty="high",
        payout={Outcome.SUCCESS: {"stamina": 1}},
    )

    result = resolve_challenge(challenge, actor, roll=0.3)

    assert result.challenge_name == "Lift the portcullis"
    assert result.domain == "strength"
    assert result.competency_label in {"good", "very good"}
    assert result.difficulty_label == "good"
    assert result.outcome_label in {"success", "major success"}
    assert result.payout_label in {"ok", "good", "very good"}


def test_cost_modifier_makes_challenge_cheaper_or_dearer():
    base = _adventure_actor(stamina=10)
    cheap = _adventure_actor(stamina=10)
    dear = _adventure_actor(stamina=10)
    challenge = StatChallenge(name="Bribe", domain="strength", difficulty="poor",
                              cost={"stamina": 4})

    base_r = resolve_challenge(challenge, base, wallet=base, roll=0.1)
    cheap_r = resolve_challenge(
        challenge, cheap, wallet=cheap, roll=0.1,
        effects=[SituationalEffect(name="discount", cost_modifier=-0.5)],
    )
    dear_r = resolve_challenge(
        challenge, dear, wallet=dear, roll=0.1,
        effects=[SituationalEffect(name="gouged", cost_modifier=0.5)],
    )

    assert base_r.cost_paid == {"stamina": 4}
    assert cheap_r.cost_paid == {"stamina": 2}   # 4 * 0.5
    assert dear_r.cost_paid == {"stamina": 6}    # 4 * 1.5
    assert cheap.wallet["stamina"] == 8
    assert dear.wallet["stamina"] == 4


def test_reward_modifier_scales_payout():
    up = _adventure_actor()
    down = _adventure_actor()
    challenge = StatChallenge(
        name="Errand", domain="strength", difficulty="poor",
        payout=ChallengePayout(by_outcome={Outcome.SUCCESS: {"mana": 4}}),
    )

    up_r = resolve_challenge(
        challenge, up, wallet=up, roll=0.1,
        effects=[SituationalEffect(name="patron", reward_modifier=0.5)],
    )
    down_r = resolve_challenge(
        challenge, down, wallet=down, roll=0.1,
        effects=[SituationalEffect(name="skimmed", reward_modifier=-0.5)],
    )

    assert up_r.payout_granted == {"mana": 6}    # 4 * 1.5
    assert down_r.payout_granted == {"mana": 2}  # 4 * 0.5


def test_modifier_sum_is_clamped_to_unit_factor_range():
    actor = _adventure_actor(stamina=10)
    challenge = StatChallenge(name="Toll", domain="strength", difficulty="poor",
                              cost={"stamina": 4})

    result = resolve_challenge(
        challenge, actor, wallet=actor, roll=0.1,
        effects=[
            SituationalEffect(name="a", cost_modifier=0.8),
            SituationalEffect(name="b", cost_modifier=0.8),
        ],
    )
    # sum 1.6 clamps to 1.0 -> factor 2.0, not 2.6
    assert result.cost_paid == {"stamina": 8}


def test_growth_modifier_scales_training_gain_only():
    from tangl.mechanics.progression.growth import LinearGrowthHandler

    plain = _adventure_actor()
    boosted = _adventure_actor()
    challenge = StatChallenge(
        name="Drill", domain="strength", difficulty="poor",
        payout=ChallengePayout(by_outcome={Outcome.SUCCESS: {"mana": 4}}),
    )

    plain_r = resolve_challenge(
        challenge, plain, wallet=plain, roll=0.1,
        growth_handler=LinearGrowthHandler(),
    )
    boosted_r = resolve_challenge(
        challenge, boosted, wallet=boosted, roll=0.1,
        growth_handler=LinearGrowthHandler(),
        effects=[SituationalEffect(name="in the mood", growth_modifier=1.0)],
    )

    plain_gain = plain_r.growth_receipt.applied_deltas["strength"]
    boosted_gain = boosted_r.growth_receipt.applied_deltas["strength"]
    assert boosted_gain == pytest.approx(plain_gain * 2.0)
    # growth_modifier must not touch the wallet payout (reward != growth)
    assert plain_r.payout_granted == boosted_r.payout_granted


def test_reward_and_growth_modifiers_are_independent_axes():
    from tangl.mechanics.progression.growth import LinearGrowthHandler

    reward_only = _adventure_actor()
    growth_only = _adventure_actor()
    challenge = StatChallenge(
        name="Spar", domain="strength", difficulty="poor",
        payout=ChallengePayout(by_outcome={Outcome.SUCCESS: {"mana": 4}}),
    )

    r = resolve_challenge(
        challenge, reward_only, wallet=reward_only, roll=0.1,
        growth_handler=LinearGrowthHandler(),
        effects=[SituationalEffect(name="bonus pay", reward_modifier=0.5)],
    )
    g = resolve_challenge(
        challenge, growth_only, wallet=growth_only, roll=0.1,
        growth_handler=LinearGrowthHandler(),
        effects=[SituationalEffect(name="good teacher", growth_modifier=0.5)],
    )

    # reward_modifier moved payout, left growth at baseline.
    assert r.payout_granted == {"mana": 6}
    # growth_modifier moved growth, left payout at baseline.
    assert g.payout_granted == {"mana": 4}
    assert (
        g.growth_receipt.applied_deltas["strength"]
        > r.growth_receipt.applied_deltas["strength"]
    )


def test_projection_helpers_remain_monotone():
    projected = [project_quality(value) for value in [4.0, 7.0, 10.0, 13.0, 16.0]]
    assert projected == sorted(projected)

    payout_qualities = [
        project_payout_quality({"gold": amount})
        for amount in [0, 1, 2, 4, 6]
    ]
    assert payout_qualities[0] is None
    assert payout_qualities[1:] == sorted(payout_qualities[1:])


def test_donor_effects_and_tags_are_applied_deterministically():
    actor = _adventure_actor()
    sword = SituationalEffect(
        name="Sword of Kings",
        applies_to_tags={"#combat"},
        applies_to_stats={"strength"},
        competency_modifier=1.0,
    )
    arena = SituationalEffect(
        name="Arena roar",
        applies_to_tags={"#arena"},
        competency_modifier=0.5,
    )
    fatigue = SituationalEffect(
        name="Fatigue",
        difficulty_modifier=0.25,
    )

    challenge = StatChallenge(domain="strength", difficulty="high", tags={"#combat"})
    result = resolve_challenge(
        challenge,
        actor,
        effect_donors=[SimpleEffectDonor(sword, arena, fatigue)],
        tag_donors=[SimpleTagDonor("#arena")],
        roll=0.4,
    )

    assert [effect.name for effect in result.active_effects] == [
        "Sword of Kings",
        "Arena roar",
        "Fatigue",
    ]


def test_modifier_clamping_limits_effective_competency_bonus():
    actor = _adventure_actor(strength=10.0)
    effects = [
        SituationalEffect(
            name=f"Buff {idx}",
            applies_to_tags={"#combat"},
            applies_to_stats={"strength"},
            competency_modifier=0.7,
        )
        for idx in range(10)
    ]

    baseline = resolve_challenge(
        StatChallenge(domain="strength", difficulty=10.0, tags={"#combat"}),
        actor,
        roll=0.5,
    )
    buffed = resolve_challenge(
        StatChallenge(domain="strength", difficulty=10.0, tags={"#combat"}),
        actor,
        effects=effects,
        roll=0.5,
    )

    assert buffed.effective_competency - baseline.effective_competency <= 2.5 + 1e-6


def test_stat_requirements_gate_broad_resources():
    system = _social_system()
    stats = HasStats.from_system(
        system,
        overrides={"strength": 10.0, "magic": 10.0, "wealth": "high"},
    ).stats
    wallet = HasWallet(wallet={})
    actor = Adventurer(stat_system=system, stats=stats, wallet=wallet.wallet)

    open_gate = StatChallenge(domain="strength", difficulty=10.0, requirements={"wealth": "good"})
    assert resolve_challenge(open_gate, actor, roll=0.5).outcome in Outcome

    locked_gate = StatChallenge(
        domain="strength",
        difficulty=10.0,
        requirements={"wealth": {"maximum": "poor"}},
    )
    try:
        resolve_challenge(locked_gate, actor, roll=0.5)
    except ValueError as exc:
        assert "requirements" in str(exc)
    else:
        raise AssertionError("Expected a gated challenge to raise")


def test_opposed_challenge_uses_defender_competency_as_difficulty():
    attacker = _adventure_actor(strength=14.0)
    defender = _adventure_actor(strength=12.0)
    challenge = StatChallenge(domain="strength", difficulty="very poor")

    result = resolve_challenge(challenge, attacker, defender=defender, roll=0.5)

    assert abs(result.effective_difficulty - defender.compute_competency("strength")) < 1e-6


def test_domain_and_wallet_remaps_are_applied_via_effects():
    actor = _adventure_actor(strength=8.0, magic=14.0, stamina=0, mana=4)
    remap = SituationalEffect(
        name="Hexed trial",
        applies_to_tags={"#hex"},
        domain_override="magic",
        cost_currency_remap={"stamina": "mana"},
        reward_currency_remap={"stamina": "mana"},
    )
    challenge = StatChallenge(
        domain="strength",
        difficulty="mid",
        cost={"stamina": 1},
        payout={Outcome.SUCCESS: {"stamina": 1}},
        tags={"#hex"},
    )

    result = resolve_challenge(
        challenge,
        actor,
        wallet=actor,
        effects=[remap],
        roll=0.4,
    )

    assert result.domain == "magic"
    assert result.cost_paid == {"mana": 1}
    assert "mana" in result.payout_granted
    assert actor.wallet["mana"] >= 3


def test_situational_effect_remaps_are_immutable_and_serializable():
    effect = SituationalEffect(cost_currency_remap={"stamina": "mana"})
    default_effect = SituationalEffect()

    with pytest.raises(TypeError):
        effect.cost_currency_remap["stamina"] = "gold"
    with pytest.raises(TypeError):
        default_effect.cost_currency_remap["stamina"] = "mana"

    assert effect.model_dump()["cost_currency_remap"] == {"stamina": "mana"}
    assert effect.model_copy(deep=True).cost_currency_remap == {"stamina": "mana"}
