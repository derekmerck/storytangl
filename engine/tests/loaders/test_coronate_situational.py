"""Phase 5 slice: the Regent drives the situational-effect layer.

Closes the Phase-2 gap (cost/difficulty/reward/growth modifiers had unit
coverage but no world consumer). The Regent is an EffectDonor: mood biases
*training growth* via a growth_modifier scoped to the skill-category tag, and
the dragonslayer sword eases the dragon check via a difficulty_modifier.
These are mechanical biases (clamped, probabilistic), proven deterministically
at the resolve_challenge level rather than through flaky traversal.
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
    import coronate_the_regent.domain as d  # noqa: WPS433

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


class TestSwordEasesDragonCheck:
    def _dragon(self, with_sword: bool):
        d = _domain()
        regent = d.Regent()
        if with_sword:
            regent.inv.add("dragonslayer_sword")
        challenge = d.DragonFight._challenge
        return resolve_challenge(
            challenge,
            regent,
            effect_donors=(regent,),
            tag_donors=(regent,),
            roll=0.5,
        )

    def test_sword_lowers_effective_difficulty_and_raises_odds(self) -> None:
        without = self._dragon(with_sword=False)
        withit = self._dragon(with_sword=True)
        # The sword is a clamped difficulty malus on the #dragon-tagged check.
        assert withit.effective_difficulty < without.effective_difficulty
        assert withit.success_likelihood > without.success_likelihood

    def test_sword_effect_is_active_in_the_result(self) -> None:
        result = self._dragon(with_sword=True)
        assert any(
            e.name == "dragonslayer sword" for e in result.active_effects
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
