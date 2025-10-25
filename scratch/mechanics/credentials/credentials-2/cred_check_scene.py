"""
A CredentialCheckScene includes series of CredentialCheckChallenges
that all operate under the same CredentiallingRules.

The candidates to be reviewed may be _fixed_ or generated _dynamically_
using extras.

Each candidate's IndicatedDisposition may be _fixed_ or generated
_dynamically_ according to a sample distribution for pass/deny/arrest.
"""
from __future__ import annotations
from typing import Iterable
import random

from tangl.type_hints import UniqueLabel
from tangl.graph.mixins import TraversalHandler, Edge
from tangl.story.scene import Scene
from tangl.story.actor.extras import Extras
from tangl.mechanics.credential.enums import Outcome, RestrictionMap, Indication

from .cred_check_challenge import CredCheckChallenge

CredentialingRules = dict

class CredCheckScene(Scene):

    restriction_map: RestrictionMap

    num_challenges: int = 3
    outcomes_distribution: dict[Outcome, float]
    extras_distribution: dict[Extras, float]

    @property
    def challenges(self) -> list[CredCheckChallenge]:
        return self.find_children(CredCheckChallenge)

    def cast_extras(self, n: int = 1):
        # extras = random.choices(
        #     list(self.extras_distribution.keys()),
        #     list(self.extras_distribution.values()),
        #     k=n)
        ...

    @TraversalHandler.enter_strategy
    def _create_challenges(self, with_edge: Edge = None):
        if self.num_challenges < len(self.challenges):

            def sample_outcomes() -> list[Outcome]:
                return random.choices(
                    list(self.outcomes_distribution.keys()),
                    weights=list(self.outcomes_distribution.values()),
                    k = self.num_challenges - len(self.challenges)
                )

            for outcome in sample_outcomes():
                extra = self.cast_extras(1)
                indication = Indication.from_outcome_and_restrictions(outcome, self.restriction_map)
                ch = CredCheckChallenge(
                    candidate = extra,
                    indication = indication,
                    expected_outcome = outcome,
                    parent = self
                )
                self.add_child(ch)

    # we don't really need to do this until we are pretty sure that we are going to enter
    _create_challenges.priority = 70

