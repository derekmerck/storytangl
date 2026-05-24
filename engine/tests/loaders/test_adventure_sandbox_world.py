"""Tests for the Adventure-style sandbox demo world bundle."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.sandbox import SandboxLocation
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _adventure_root() -> Path:
    return _repo_worlds_dir() / "adventure_sandbox_slice"


def _provision_sandbox_actions(ledger: Ledger) -> list[Action]:
    assert isinstance(ledger.cursor, SandboxLocation)
    do_provision(
        ledger.cursor,
        ctx=PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid),
    )
    return [
        edge
        for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(edge.tags)
    ]


def _choose(ledger: Ledger, **hints: str) -> Action:
    for action in _provision_sandbox_actions(ledger):
        action_hints = action.ui_hints.model_dump()
        if all(action_hints.get(key) == value for key, value in hints.items()):
            ledger.resolve_choice(action.uid, choice_payload=action.payload)
            return action
    raise AssertionError(f"No sandbox action at {ledger.cursor.label!r} matched {hints!r}")


class TestAdventureSandboxWorld:
    """Tests for the real Adventure-style sandbox demo world."""

    def test_world_registry_discovers_adventure_sandbox_slice(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "adventure_sandbox_slice" in registry.bundles
        bundle = registry.bundles["adventure_sandbox_slice"]
        assert bundle.manifest.label == "adventure_sandbox_slice"
        assert bundle.manifest.metadata["title"] == "Adventure Sandbox Slice"

    def test_adventure_sandbox_world_runs_core_walkthrough(self) -> None:
        bundle = WorldBundle.load(_adventure_root())
        world = WorldCompiler().compile(bundle)

        assert "AdventureSandboxLocation" in world.class_registry

        result = world.create_story("adventure_sandbox_slice", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        enter = next(
            edge
            for edge in ledger.cursor.edges_out()
            if isinstance(edge, Action)
            and edge.text == "Stand at the end of the road"
        )
        ledger.resolve_choice(enter.uid)

        assert ledger.cursor.label == "road"

        _choose(ledger, contribution="movement", direction="east")
        _choose(ledger, contribution="take", asset="keys")
        _choose(ledger, contribution="take", asset="brass_lamp")
        _choose(ledger, contribution="light", asset="brass_lamp", verb="turn_on")
        _choose(ledger, contribution="movement", direction="west")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="unlock", target="grate")
        _choose(ledger, contribution="open", target="grate")
        _choose(ledger, contribution="movement", direction="down")
        _choose(ledger, contribution="movement", direction="west")

        assert ledger.cursor.label == "cobble_crawl"

        _choose(ledger, contribution="mob", mob="wounded_pirate", action="help")

        content = [
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment, ContentFragment)
        ]
        assert "The key turns with a click. The grate unlocks." in content
        assert "A wounded pirate leans against the wall, watching you." in content
        assert "The pirate eyes you suspiciously, but accepts your help." in content
