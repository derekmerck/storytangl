"""Tests for the composite colony loop world bundle."""

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


def _colony_root() -> Path:
    return _repo_worlds_dir() / "colony_loop"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestColonyLoopWorld:
    """Tests for the colony composite demo world."""

    def test_world_registry_discovers_colony_loop(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "colony_loop" in registry.bundles
        bundle = registry.bundles["colony_loop"]
        assert bundle.manifest.label == "colony_loop"
        assert bundle.manifest.metadata["title"] == "Colony Loop"

    def test_colony_loop_compiles_and_writes_back_contest_victory(self) -> None:
        bundle = WorldBundle.load(_colony_root())
        world = WorldCompiler().compile(bundle)

        assert "ColonyShellBlock" in world.class_registry
        assert "ColonyContestBlock" in world.class_registry

        result = world.create_story("colony_loop_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        ledger.resolve_choice(_actions(ledger)[0].uid)

        assert ledger.cursor.label == "shell"
        promote = next(action for action in _actions(ledger) if action.label == "Promote 1 worker into guard")
        ledger.resolve_choice(promote.uid, choice_payload=promote.payload)

        challenge = next(action for action in _actions(ledger) if action.text == "Challenge the rival nest")
        ledger.resolve_choice(challenge.uid)

        assert ledger.cursor.label == "contest"
        commit = next(action for action in _actions(ledger) if action.label == "Commit 2 rock")
        ledger.resolve_choice(commit.uid, choice_payload=commit.payload)

        assert ledger.cursor.label == "raid_won"
        ledger.resolve_choice(_actions(ledger)[0].uid)

        assert ledger.cursor.label == "victory"

        shell = next(node for node in result.graph.find_nodes(Selector(has_kind=world.class_registry["ColonyShellBlock"])))
        assert shell.game.resources["rock"] == 1
        assert shell.game.resources["scrap"] == 2
        assert "tribute_store" in shell.game.unlocked_builds
        assert shell.locals["tribute_active"] is True
        assert shell.locals["rival_defeated"] is True
