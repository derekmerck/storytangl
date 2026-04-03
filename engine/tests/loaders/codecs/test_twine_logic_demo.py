"""Integration tests for the Twine-authored logic demo world."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import Action, InitMode, World
from tangl.vm import Ledger


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[4] / "worlds" / "twine_logic_demo"


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def test_twine_logic_demo_bundle_loads() -> None:
    root = _logic_root()
    bundle = WorldBundle.load(root)

    assert bundle.manifest.label == "twine_logic_demo"
    assert bundle.get_story_codec() == "twee3_1_0"
    assert bundle.get_script_paths() == [root / "story.twee"]


def test_twine_logic_demo_world_compiles() -> None:
    bundle = WorldBundle.load(_logic_root())
    world = WorldCompiler().compile(bundle)

    assert isinstance(world, World)
    assert world.metadata["title"] == "Twine Logic Demo"
    assert world.bundle.codec_id == "twee3_1_0"
    assert world.bundle.entry_template_ids == ["world.start"]
    assert world.bundle.codec_state["story_format"] == "Twine 2"


def test_twine_logic_demo_parity_traversal_reaches_expected_outputs() -> None:
    bundle = WorldBundle.load(_logic_root())
    world = WorldCompiler().compile(bundle)

    even_story = world.create_story("twine_logic_demo_even", init_mode=InitMode.EAGER)
    even_ledger = Ledger.from_graph(even_story.graph, entry_id=even_story.graph.initial_cursor_id)
    even_ledger.resolve_choice(_choice_by_text(even_ledger, "Begin parity checker").uid)
    even_ledger.resolve_choice(_choice_by_text(even_ledger, "First bit = 1").uid)
    even_ledger.resolve_choice(_choice_by_text(even_ledger, "Second bit = 1").uid)

    odd_story = world.create_story("twine_logic_demo_odd", init_mode=InitMode.EAGER)
    odd_ledger = Ledger.from_graph(odd_story.graph, entry_id=odd_story.graph.initial_cursor_id)
    odd_ledger.resolve_choice(_choice_by_text(odd_ledger, "Begin parity checker").uid)
    odd_ledger.resolve_choice(_choice_by_text(odd_ledger, "First bit = 0").uid)
    odd_ledger.resolve_choice(_choice_by_text(odd_ledger, "Second bit = 1").uid)

    assert even_ledger.cursor.label == "evenoutput"
    assert odd_ledger.cursor.label == "oddoutput"
