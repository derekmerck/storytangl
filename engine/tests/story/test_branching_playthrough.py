from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Sequence

import pytest
import yaml

from tangl.core import BaseFragment, StreamRegistry
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger

from helpers.fragment_helpers import extract_fragments, extract_all_choices


def _load_branching_ledger(resources_dir: Path, label: str) -> tuple[Ledger, Frame]:
    script_path = resources_dir / "demo_script.yaml"
    data = yaml.safe_load(script_path.read_text())

    script_manager = ScriptManager.from_data(data)
    world = World(label=f"{label}_world", script_manager=script_manager)
    story = world.create_story(f"{label}_story")

    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label=f"{label}_ledger",
    )
    ledger.push_snapshot()
    ledger.init_cursor()
    frame = ledger.get_frame()
    return ledger, frame


def _step_fragments(ledger: Ledger, step_index: int) -> list[BaseFragment]:
    marker = f"step-{step_index:04d}"
    fragments = list(ledger.get_journal(marker))
    assert fragments, f"No fragments recorded for {marker}"
    return fragments


def _fragments_of_type(
    fragments: Iterable[BaseFragment], fragment_type: str
) -> list[BaseFragment]:
    return extract_fragments(fragments, fragment_type)


def _choice_contents(fragments: Iterable[BaseFragment]) -> Sequence[str]:
    return [f.content for f in extract_all_choices(fragments)]


@pytest.fixture(autouse=True)
def _clear_worlds() -> None:
    World.clear_instances()
    yield
    World.clear_instances()


def test_branching_left_path_walkthrough(resources_dir: Path) -> None:
    ledger, frame = _load_branching_ledger(resources_dir, "left_path")
    assert frame.cursor.label == "start"

    step1 = _step_fragments(ledger, 1)
    block_fragments = _fragments_of_type(step1, "block")
    assert block_fragments and "crossroads" in block_fragments[0].content.lower()

    choices = _fragments_of_type(step1, "choice")
    assert len(choices) >= 2
    assert any("left" in fragment.content.lower() for fragment in choices)
    assert any("right" in fragment.content.lower() for fragment in choices)

    assert "guide" in ledger.graph.all_labels()
    assert 'guide' in [c.label for c in ledger.graph.get(ledger.cursor_id).get_concepts()]

    assert any("guide" in fragment.content.lower() for fragment in choices)

    left_choice = next(fragment for fragment in choices if "left" in fragment.content.lower())
    left_edge = ledger.graph.get(left_choice.source_id)
    frame.follow_edge(left_edge)
    assert frame.cursor.label == "entrance"

    step2 = _step_fragments(ledger, 2)
    garden_block = _fragments_of_type(step2, "block")
    assert garden_block and "garden" in garden_block[0].content.lower()

    finale_edge = next(
        edge
        for edge in ledger.graph.find_edges(source_id=frame.cursor_id)
        if getattr(ledger.graph.get(edge.destination_id), "label", None) == "finale"
    )
    frame.follow_edge(finale_edge)
    assert frame.cursor.label == "finale"

    step3 = _step_fragments(ledger, 3)
    final_block = _fragments_of_type(step3, "block")
    assert final_block and "adventure comes to an end" in final_block[0].content.lower()
    assert not _fragments_of_type(step3, "choice")


def test_branching_right_path_walkthrough(resources_dir: Path) -> None:
    ledger, frame = _load_branching_ledger(resources_dir, "right_path")

    step1 = _step_fragments(ledger, 1)
    choices = _fragments_of_type(step1, "choice")
    right_choice = next(fragment for fragment in choices if "right" in fragment.content.lower())
    frame.follow_edge(ledger.graph.get(right_choice.source_id))
    assert frame.cursor.label == "entrance"

    step2 = _step_fragments(ledger, 2)
    cave_block = _fragments_of_type(step2, "block")
    assert cave_block and "dark cave" in cave_block[0].content.lower()

    step2_choice_texts = {content.lower() for content in _choice_contents(step2)}
    assert {"enter_the_cave", "go_back"} <= step2_choice_texts

    enter_choice = next(fragment for fragment in _fragments_of_type(step2, "choice") if "enter" in fragment.content.lower())
    frame.follow_edge(ledger.graph.get(enter_choice.source_id))
    assert frame.cursor.label == "interior"

    step3 = _step_fragments(ledger, 3)
    interior_block = _fragments_of_type(step3, "block")
    assert interior_block and "deeper" in interior_block[0].content.lower()

    finale_edge = next(
        edge
        for edge in ledger.graph.find_edges(source_id=frame.cursor_id)
        if getattr(ledger.graph.get(edge.destination_id), "label", None) == "finale"
    )
    frame.follow_edge(finale_edge)
    assert frame.cursor.label == "finale"

    step4 = _step_fragments(ledger, 4)
    final_block = _fragments_of_type(step4, "block")
    assert final_block and "adventure comes to an end" in final_block[0].content.lower()
    assert not _fragments_of_type(step4, "choice")


def test_branching_backtrack_then_garden(resources_dir: Path) -> None:
    ledger, frame = _load_branching_ledger(resources_dir, "backtrack")

    step1 = _step_fragments(ledger, 1)
    right_choice = next(
        fragment for fragment in _fragments_of_type(step1, "choice") if "right" in fragment.content.lower()
    )
    frame.follow_edge(ledger.graph.get(right_choice.source_id))
    assert frame.cursor.label == "entrance"

    step2 = _step_fragments(ledger, 2)
    go_back_choice = next(
        fragment for fragment in _fragments_of_type(step2, "choice") if "back" in fragment.content.lower()
    )
    frame.follow_edge(ledger.graph.get(go_back_choice.source_id))
    assert frame.cursor.label == "start"

    step3 = _step_fragments(ledger, 3)
    loop_choices = _fragments_of_type(step3, "choice")
    assert len(loop_choices) >= 2
    assert any("left" in fragment.content.lower() for fragment in loop_choices)
    assert any("right" in fragment.content.lower() for fragment in loop_choices)

    left_choice = next(fragment for fragment in loop_choices if "left" in fragment.content.lower())
    frame.follow_edge(ledger.graph.get(left_choice.source_id))
    assert frame.cursor.label == "entrance"

    step4 = _step_fragments(ledger, 4)
    garden_block = _fragments_of_type(step4, "block")
    assert garden_block and "garden" in garden_block[0].content.lower()

    finale_edge = next(
        edge
        for edge in ledger.graph.find_edges(source_id=frame.cursor_id)
        if getattr(ledger.graph.get(edge.destination_id), "label", None) == "finale"
    )
    frame.follow_edge(finale_edge)
    assert frame.cursor.label == "finale"

    step5 = _step_fragments(ledger, 5)
    final_block = _fragments_of_type(step5, "block")
    assert final_block and "adventure comes to an end" in final_block[0].content.lower()
    assert not _fragments_of_type(step5, "choice")
