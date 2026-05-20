"""Tests for the ED queueing simulation demo world bundle."""

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


def _ed_queue_root() -> Path:
    return _repo_worlds_dir() / "ed_queue_demo"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestEdQueueDemoWorld:
    """Tests for the ED queueing simulation demo."""

    def test_world_registry_discovers_ed_queue_demo(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "ed_queue_demo" in registry.bundles
        bundle = registry.bundles["ed_queue_demo"]
        assert bundle.manifest.label == "ed_queue_demo"
        assert bundle.manifest.metadata["title"] == "ED Queue Demo"

    def test_ed_queue_demo_compiles_and_runs_to_summary(self) -> None:
        bundle = WorldBundle.load(_ed_queue_root())
        world = WorldCompiler().compile(bundle)

        assert "EdQueueBlock" in world.class_registry

        result = world.create_story("ed_queue_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        ledger.resolve_choice(_actions(ledger)[0].uid)

        assert ledger.cursor.label == "simulation"
        run_until_complete = next(
            action
            for action in _actions(ledger)
            if action.label == "Run until complete"
        )
        ledger.resolve_choice(
            run_until_complete.uid,
            choice_payload=run_until_complete.payload,
        )

        assert ledger.cursor.label == "summary"
        content = " ".join(
            getattr(fragment, "content", "")
            for fragment in ledger.get_journal()
        )
        assert "mean_los=14.0" in content
        assert "bottleneck=imaging" in content
