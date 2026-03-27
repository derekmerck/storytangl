"""Tests for the logic demo world bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _logic_root() -> Path:
    return _repo_worlds_dir() / "logic_demo"


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _install_story_media_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def _compile_logic_world():
    bundle = WorldBundle.load(_logic_root())
    return WorldCompiler().compile(bundle)


def _make_ledger(*, world, story_label: str) -> Ledger:
    result = world.create_story(story_label, init_mode=InitMode.EAGER)
    return Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)


def test_logic_demo_compiles_with_custom_domain_types(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()

    assert "LogicBlock" in world.class_registry
    assert "GateBadgeSpec" in world.class_registry

    result = world.create_story("logic_demo_loader", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

    assert ledger.cursor.label == "choose_machine"
    assert ledger.cursor.__class__.__name__ == "LogicBlock"


def test_parity_checker_routes_to_even_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    ledger = _make_ledger(world=world, story_label="logic_demo_parity_even")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the parity checker").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "First bit = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Second bit = 1").uid)

    assert ledger.cursor.label == "parity_even_output"


def test_parity_checker_routes_to_odd_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    ledger = _make_ledger(world=world, story_label="logic_demo_parity_odd")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the parity checker").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "First bit = 0").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Second bit = 1").uid)

    assert ledger.cursor.label == "parity_odd_output"


def test_half_adder_routes_all_input_pairs_to_expected_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    expectations = {
        ("A = 0", "B = 0"): "half_adder_output_00",
        ("A = 0", "B = 1"): "half_adder_output_10",
        ("A = 1", "B = 0"): "half_adder_output_10",
        ("A = 1", "B = 1"): "half_adder_output_01",
    }

    for index, ((a_choice, b_choice), expected_label) in enumerate(expectations.items()):
        ledger = _make_ledger(world=world, story_label=f"logic_demo_half_adder_{index}")
        ledger.resolve_choice(_choice_by_text(ledger, "Inspect the half adder").uid)
        ledger.resolve_choice(_choice_by_text(ledger, a_choice).uid)
        ledger.resolve_choice(_choice_by_text(ledger, b_choice).uid)

        assert ledger.cursor.label == expected_label


def test_full_adder_routes_all_input_triples_to_expected_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    expectations = {
        ("A = 0", "B = 0", "Cin = 0"): "full_adder_output_000_sc00",
        ("A = 0", "B = 0", "Cin = 1"): "full_adder_output_001_sc10",
        ("A = 0", "B = 1", "Cin = 0"): "full_adder_output_010_sc10",
        ("A = 0", "B = 1", "Cin = 1"): "full_adder_output_011_sc01",
        ("A = 1", "B = 0", "Cin = 0"): "full_adder_output_100_sc10",
        ("A = 1", "B = 0", "Cin = 1"): "full_adder_output_101_sc01",
        ("A = 1", "B = 1", "Cin = 0"): "full_adder_output_110_sc01",
        ("A = 1", "B = 1", "Cin = 1"): "full_adder_output_111_sc11",
    }

    for index, ((a_choice, b_choice, cin_choice), expected_label) in enumerate(expectations.items()):
        ledger = _make_ledger(world=world, story_label=f"logic_demo_full_adder_{index}")
        ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)
        ledger.resolve_choice(_choice_by_text(ledger, a_choice).uid)
        ledger.resolve_choice(_choice_by_text(ledger, b_choice).uid)
        ledger.resolve_choice(_choice_by_text(ledger, cin_choice).uid)

        assert ledger.cursor.label == expected_label
