"""Phase 3: thin TrainingBlock / ChallengeBlock facets over resolve_challenge.

Drives a real Ledger traversal so the proof is end-to-end: the protagonist is
found via the story `gather_player_fixture` namespace handler, the challenge
resolves in UPDATE, and authored POSTREQS edges branch on the
`challenge_passed` / `challenge_failed` predicate facts (mirroring the
HasGame `game_won` pattern). Outcomes are made deterministic with extreme
competency-vs-difficulty gaps rather than seeding RNG.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.mechanics.progression import (
    HasStatChallenge,
    HasTraining,
    HasStats,
    HasWallet,
    LinearGrowthHandler,
)
from tangl.mechanics.progression.challenges import StatChallenge
from tangl.mechanics.progression.definition import (
    CanonicalSlot,
    StatDef,
    StatSystemDefinition,
)
from tangl.story import Action, Block, Player, StoryGraph
from tangl.vm import Ledger, ResolutionPhase as P, TraversableEdge


_SYSTEM = StatSystemDefinition(
    name="trial",
    theme="test",
    complexity=2,
    handler="probit",
    stats=[
        StatDef(name="body", is_intrinsic=True, canonical_slot=CanonicalSlot.PHYSICAL),
        StatDef(name="grit", governed_by="body"),
    ],
)


class Hero(Player, HasStats, HasWallet):
    """Inline protagonist composing the story Player with progression mixins."""


Hero.model_rebuild(_types_namespace={"UUID": UUID})


def _hero(level: float) -> Hero:
    stats = HasStats.from_system(_SYSTEM, overrides={"body": level, "grit": level}).stats
    return Hero(stat_system=_SYSTEM, stats=stats, wallet={})


class TrialBlock(HasStatChallenge, Block):
    _challenge = StatChallenge(name="The Trial", domain="grit", difficulty=1.0)


class DrillBlock(HasTraining, Block):
    _training_skill = "grit"
    _training_difficulty = "ok"
    _growth_handler = LinearGrowthHandler()


TrialBlock.model_rebuild(_types_namespace={"UUID": UUID})
DrillBlock.model_rebuild(_types_namespace={"UUID": UUID})


def _challenge_world(hero: Hero, challenge: StatChallenge):
    graph = StoryGraph(label="trial")
    graph.add(hero)

    start = Block(label="start", content="Start")
    graph.add(start)
    trial = TrialBlock(label="trial", content="Face the trial")
    object.__setattr__(trial, "_challenge", challenge)
    graph.add(trial)
    won = Block(label="won", content="You prevailed")
    lost = Block(label="lost", content="You fell")
    graph.add(won)
    graph.add(lost)

    graph.add(Action(predecessor_id=start.uid, successor_id=trial.uid, text="Begin"))
    graph.add(
        TraversableEdge(
            graph=graph,
            predecessor_id=trial.uid,
            successor_id=won.uid,
            trigger_phase=P.POSTREQS,
            predicate="challenge_passed",
            label="passed",
        )
    )
    graph.add(
        TraversableEdge(
            graph=graph,
            predecessor_id=trial.uid,
            successor_id=lost.uid,
            trigger_phase=P.POSTREQS,
            predicate="challenge_failed",
            label="failed",
        )
    )
    graph.initial_cursor_id = start.uid
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    begin = next(iter(start.edges_out(Selector(has_kind=Action))))
    return ledger, begin


class TestChallengeBlockBranches:
    def test_strong_hero_passes_and_routes_to_won(self) -> None:
        hero = _hero(level=18.0)
        challenge = StatChallenge(name="Easy Trial", domain="grit", difficulty=1.0)
        ledger, begin = _challenge_world(hero, challenge)

        ledger.resolve_choice(begin.uid)

        assert ledger.cursor.label == "won"

    def test_weak_hero_fails_and_routes_to_lost(self) -> None:
        hero = _hero(level=2.0)
        challenge = StatChallenge(name="Brutal Trial", domain="grit", difficulty=20.0)
        ledger, begin = _challenge_world(hero, challenge)

        ledger.resolve_choice(begin.uid)

        assert ledger.cursor.label == "lost"

    def test_challenge_facts_published_to_namespace(self) -> None:
        hero = _hero(level=18.0)
        challenge = StatChallenge(name="Easy Trial", domain="grit", difficulty=1.0)
        ledger, begin = _challenge_world(hero, challenge)

        ledger.resolve_choice(begin.uid)

        trial = ledger.graph.find_one(Selector(has_kind=TrialBlock))
        assert trial.locals["challenge_passed"] is True
        assert trial.locals["challenge_failed"] is False
        assert trial.locals["challenge_quality"]


class TestTrainingBlockGrows:
    def test_training_raises_the_skill(self) -> None:
        hero = _hero(level=8.0)
        graph = StoryGraph(label="drill")
        graph.add(hero)
        start = Block(label="start", content="Start")
        drill = DrillBlock(label="drill", content="Train hard")
        graph.add(start)
        graph.add(drill)
        graph.add(
            Action(predecessor_id=start.uid, successor_id=drill.uid, text="Train")
        )
        graph.initial_cursor_id = start.uid
        ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
        begin = next(iter(start.edges_out(Selector(has_kind=Action))))

        before = hero.stats["grit"].fv
        ledger.resolve_choice(begin.uid)
        after = hero.stats["grit"].fv

        assert after > before
        assert drill.locals["trained_skill"] == "grit"
        assert drill.locals["trained_gain"] > 0.0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
