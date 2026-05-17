"""Phase 5 slice: the Regent drives the situational-effect layer.

Closes the Phase-2 gap (cost/difficulty/reward/growth modifiers had unit
coverage but no world consumer). The Regent is an EffectDonor: mood biases
*training growth* via a growth_modifier scoped to the skill-category tag, and
the dragonslayer sword forces the dragon check to a pass via forced_outcome.
Proven deterministically at the resolve_challenge level rather than through
flaky traversal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tangl.mechanics.progression import LinearGrowthHandler
from tangl.mechanics.progression.challenges import StatChallenge, resolve_challenge


def _domain():
    root = Path(__file__).resolve().parents[3] / "worlds" / "coronate_the_regent"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import coronate_the_regent.domain as d

    return d


class TestMoodBiasesTrainingGrowth:
    def _train(self, mood):
        d = _domain()
        regent = d.Regent(mood=mood)
        challenge = StatChallenge(
            name="drill", domain="combat", difficulty=0.0,
            tags={"training", "#martial"},
        )
        result = resolve_challenge(
            challenge,
            regent,
            effect_donors=(regent,),
            tag_donors=(regent,),
            growth_handler=LinearGrowthHandler(),
            roll=0.0,  # deterministic outcome; growth differs only by mood
        )
        return result.growth_receipt.applied_deltas["combat"]

    def test_martial_mood_grows_combat_faster_than_no_mood(self) -> None:
        plain = self._train(mood=None)
        martial = self._train(mood="martial")
        assert martial == pytest.approx(plain * 2.0)  # growth_modifier +1.0

    def test_wrong_mood_does_not_boost_offcategory_training(self) -> None:
        plain = self._train(mood=None)
        studious = self._train(mood="studious")  # only buffs #courtly
        assert studious == pytest.approx(plain)


class TestSwordForcesDragonOutcome:
    def _dragon(self, with_sword: bool):
        d = _domain()
        regent = d.Regent()
        if with_sword:
            regent.inv.add("dragonslayer_sword")
        # roll=0.99 would fail the difficulty-20 check on its own; the sword
        # must override that deterministically.
        return resolve_challenge(
            d.DragonFight._challenge,
            regent,
            effect_donors=(regent,),
            tag_donors=(regent,),
            roll=0.99,
        )

    def test_without_sword_the_hard_check_fails(self) -> None:
        from tangl.mechanics.progression import Outcome

        assert self._dragon(with_sword=False).outcome < Outcome.SUCCESS

    def test_sword_forces_a_pass_regardless_of_roll(self) -> None:
        from tangl.mechanics.progression import Outcome

        result = self._dragon(with_sword=True)
        assert result.outcome == Outcome.MAJOR_SUCCESS
        assert any(
            e.name == "dragonslayer sword" for e in result.active_effects
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
