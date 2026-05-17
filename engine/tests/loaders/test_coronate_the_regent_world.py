"""Phase 4: the four acceptance paths for Coronate the Regent.

Each path proves a different mechanical solution to the same terminal
crisis, asserting end state, the inter-phase causal flags, and journal text
(not just the terminal block) -- the demo's reason to exist.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import Action, InitMode, Player
from tangl.vm import Ledger


def _root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "coronate_the_regent"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _choose(ledger: Ledger, text: str) -> None:
    action = next(a for a in _actions(ledger) if (a.text or a.label) == text)
    ledger.resolve_choice(action.uid)


def _journal_text(ledger: Ledger) -> str:
    parts: list[str] = []
    for record in ledger.output_stream:
        content = getattr(record, "content", None)
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


@pytest.fixture
def world():
    """Compile the world per test (per-test singleton cleanup makes this safe)."""
    return WorldCompiler().compile(WorldBundle.load(_root()))


def _play(world, choices: list[str]):
    result = world.create_story(f"ctr_{uuid4().hex}", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(
        result.graph, entry_id=result.graph.initial_cursor_id
    )
    for text in choices:
        _choose(ledger, text)
    regent = result.graph.find_one(Selector(has_kind=Player))
    return ledger, regent


class TestCoronateTheRegentAcceptancePaths:
    def test_world_compiles_and_registers_domain(self, world) -> None:
        assert "PrinceAudience" in world.class_registry
        assert "DragonFight" in world.class_registry

    def test_courtly_survivor_marries_the_prince(self, world) -> None:
        ledger, regent = _play(
            world,
            [
                "Begin the first week",
                "Study courtly graces",          # w1
                "Receive the visiting prince",   # w2 -> pass -> impressed
                "Leave the dragon undisturbed",  # w3
                "Move on",                       # merchant
            ]
        )
        assert ledger.cursor.label == "ending_marry"
        assert regent.has("impressed_prince")
        assert not regent.has("irritated_dragon")
        text = _journal_text(ledger)
        assert "prince" in text.lower()
        assert "betrothed" in text.lower()

    def test_martial_survivor_reigns_alone(self, world) -> None:
        ledger, regent = _play(
            world,
            [
                "Begin the first week",
                "Train at arms",                 # w1
                "Train at arms instead",         # w2 (skip prince)
                "Leave the dragon undisturbed",  # w3
                "Move on",                       # merchant
            ]
        )
        assert ledger.cursor.label == "ending_solo"
        assert not regent.has("impressed_prince")
        assert "train" in _journal_text(ledger).lower()

    def test_prepared_survivor_slays_dragon_with_sword(self, world) -> None:
        ledger, regent = _play(
            world,
            [
                "Begin the first week",
                "Study courtly graces",
                "Receive the visiting prince",        # impressed
                "Send a sharp warning to the dragon",  # irritated
                "Buy the dragonslayer sword (3 coin)",
            ]
        )
        assert ledger.cursor.label == "ending_slain_married"
        assert regent.has("dragonslayer_sword")
        assert regent.has("irritated_dragon", "impressed_prince")
        assert regent.wallet["coin"] == 0  # 3 spent
        text = _journal_text(ledger).lower()
        assert "dragon falls" in text

    def test_doomed_heir_dies_to_the_dragon(self, world) -> None:
        ledger, regent = _play(
            world,
            [
                "Begin the first week",
                "Train at arms",
                "Train at arms instead",
                "Send a sharp warning to the dragon",  # irritated, no sword
                "Move on",
            ]
        )
        assert ledger.cursor.label == "ending_dead"
        assert regent.has("irritated_dragon")
        assert not regent.has("dragonslayer_sword")
        assert "fire ends the regency" in _journal_text(ledger).lower()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
