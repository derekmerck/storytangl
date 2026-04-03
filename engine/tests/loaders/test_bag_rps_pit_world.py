"""Tests for the Bag-RPS pit demo world bundle."""

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


def _bag_rps_root() -> Path:
    return _repo_worlds_dir() / "bag_rps_pit"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestBagRpsPitWorld:
    """Tests for the Bag-RPS pit demo world."""

    def test_world_registry_discovers_bag_rps_pit(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "bag_rps_pit" in registry.bundles
        bundle = registry.bundles["bag_rps_pit"]
        assert bundle.manifest.label == "bag_rps_pit"
        assert bundle.manifest.metadata["title"] == "Bag RPS Pit"

    def test_bag_rps_pit_compiles_and_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_bag_rps_root())
        world = WorldCompiler().compile(bundle)

        assert "BagRpsPitBlock" in world.class_registry

        result = world.create_story("bag_rps_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        intro_action = _actions(ledger)[0]
        ledger.resolve_choice(intro_action.uid)

        assert ledger.cursor.label == "challenge"
        commit = next(action for action in _actions(ledger) if action.label == "Commit 2 rock")
        ledger.resolve_choice(commit.uid, choice_payload=commit.payload)

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "reserve now stands" in content.lower()
