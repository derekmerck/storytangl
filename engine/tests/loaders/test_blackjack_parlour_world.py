"""Tests for the blackjack parlour demo world bundle."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _blackjack_root() -> Path:
    return _repo_worlds_dir() / "blackjack_parlour"


def _single_choice_action(ledger: Ledger) -> Action:
    actions = list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    assert len(actions) == 1
    return actions[0]


class TestBlackjackParlourWorld:
    """Tests for the blackjack parlour demo world."""

    def test_world_registry_discovers_blackjack_parlour(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "blackjack_parlour" in registry.bundles
        bundle = registry.bundles["blackjack_parlour"]
        assert bundle.manifest.label == "blackjack_parlour"
        assert bundle.manifest.metadata["title"] == "Blackjack Parlour"

    def test_blackjack_parlour_compiles_and_routes_game_to_victory(self) -> None:
        bundle = WorldBundle.load(_blackjack_root())
        world = WorldCompiler().compile(bundle)

        assert "BlackjackBlock" in world.class_registry

        result = world.create_story("blackjack_parlour_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        intro_action = _single_choice_action(ledger)
        ledger.resolve_choice(intro_action.uid)

        assert ledger.cursor.label == "challenge"
        assert ledger.cursor.__class__.__name__ == "BlackjackBlock"

        stand = next(
            action
            for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
            if action.label == "Stand"
        )
        ledger.resolve_choice(stand.uid, choice_payload=stand.payload)

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "dealer reveals" in content.lower()
