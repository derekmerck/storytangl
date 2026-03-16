"""Tests for the RPS tavern demo world bundle.

Organized by behavior:
- Discovery: the modernized bundle loads through WorldRegistry without errors.
- Gameplay: the authored HasGame block pattern compiles and traverses to victory.
"""
from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.mechanics.games.rps_game import RpsMove
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _rps_root() -> Path:
    return _repo_worlds_dir() / "rps_tavern"


def _single_choice_action(ledger: Ledger) -> Action:
    actions = list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    assert len(actions) == 1
    return actions[0]


class TestRpsTavernWorld:
    """Tests for the RPS tavern demo world."""

    def test_world_registry_discovers_rps_tavern(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "rps_tavern" in registry.bundles
        bundle = registry.bundles["rps_tavern"]
        assert bundle.manifest.label == "rps_tavern"
        assert bundle.manifest.metadata["title"] == "RPS Tavern"

    def test_rps_tavern_compiles_and_routes_game_to_victory(self) -> None:
        bundle = WorldBundle.load(_rps_root())
        world = WorldCompiler().compile(bundle)

        assert world.domain is not None
        assert "RpsBlock" in world.domain.class_registry

        result = world.create_story("rps_tavern_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        intro_action = _single_choice_action(ledger)
        ledger.resolve_choice(intro_action.uid)

        assert ledger.cursor.label == "challenge"
        assert ledger.cursor.__class__.__name__ == "RpsBlock"

        for round_number in (1, 2):
            game_actions = [
                action
                for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
                if action.payload
            ]
            rock_action = next(
                action
                for action in game_actions
                if action.payload.get("move") == RpsMove.ROCK
            )

            ledger.resolve_choice(rock_action.uid, choice_payload=rock_action.payload)

            if round_number == 1:
                assert ledger.cursor.label == "challenge"
                assert ledger.cursor.game.round == 1
                assert ledger.cursor.game.score["player"] == 1

        assert ledger.cursor.label == "victory"
        assert ledger.cursor_history
