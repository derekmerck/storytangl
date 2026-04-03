"""Tests for the incremental yard demo world bundle."""

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


def _yard_root() -> Path:
    return _repo_worlds_dir() / "incremental_yard"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestIncrementalYardWorld:
    """Tests for the incremental yard demo world."""

    def test_world_registry_discovers_incremental_yard(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "incremental_yard" in registry.bundles
        bundle = registry.bundles["incremental_yard"]
        assert bundle.manifest.label == "incremental_yard"
        assert bundle.manifest.metadata["title"] == "Incremental Yard"

    def test_incremental_yard_compiles_and_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_yard_root())
        world = WorldCompiler().compile(bundle)

        assert "IncrementalYardBlock" in world.class_registry

        result = world.create_story("incremental_yard_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        intro_action = _actions(ledger)[0]
        ledger.resolve_choice(intro_action.uid)

        assert ledger.cursor.label == "challenge"
        assign = next(action for action in _actions(ledger) if action.label == "Assign 1 worker to scavenge")
        ledger.resolve_choice(assign.uid, choice_payload=assign.payload)

        end_cycle = next(action for action in _actions(ledger) if action.label == "End cycle")
        ledger.resolve_choice(end_cycle.uid, choice_payload=end_cycle.payload)

        build = next(action for action in _actions(ledger) if action.label == "Build signal_fire")
        ledger.resolve_choice(build.uid, choice_payload=build.payload)

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "you build signal_fire" in content.lower()
