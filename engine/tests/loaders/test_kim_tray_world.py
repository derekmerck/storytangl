"""Tests for the Kim tray demo world bundle."""

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


def _kim_tray_root() -> Path:
    return _repo_worlds_dir() / "kim_tray"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestKimTrayWorld:
    """Tests for the Kim tray demo world."""

    def test_world_registry_discovers_kim_tray(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "kim_tray" in registry.bundles
        bundle = registry.bundles["kim_tray"]
        assert bundle.manifest.label == "kim_tray"
        assert bundle.manifest.metadata["title"] == "Kim Tray"

    def test_kim_tray_compiles_and_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_kim_tray_root())
        world = WorldCompiler().compile(bundle)

        assert "KimTrayBlock" in world.class_registry

        result = world.create_story("kim_tray_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        intro_action = _actions(ledger)[0]
        ledger.resolve_choice(intro_action.uid)

        assert ledger.cursor.label == "challenge"
        inspect = next(action for action in _actions(ledger) if action.label == "Inspect the material cue")
        ledger.resolve_choice(inspect.uid, choice_payload=inspect.payload)

        guess = next(action for action in _actions(ledger) if action.label == "Guess silver thimble")
        ledger.resolve_choice(guess.uid, choice_payload=guess.payload)

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "name the missing object correctly" in content.lower()
