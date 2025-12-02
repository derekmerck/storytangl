"""Tests covering complex condition evaluation and effect helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from tangl.core import StreamRegistry
from tangl.story.concepts.item import Item
from tangl.story.episode.action import Action
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger


RESOURCE_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "complex_conditions_test.yaml"
)


def _build_ledger(data: dict[str, Any]) -> Ledger:
    World.clear_instances()
    manager = ScriptManager.from_data(data)
    world = World(
        label=f"world_{uuid4().hex}",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=manager.get_story_metadata(),
    )
    story = world.create_story(f"story_{uuid4().hex}")
    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="test-ledger",
    )
    ledger.push_snapshot()
    ledger.init_cursor()
    return ledger


def _choices_by_text(frame: Frame) -> dict[str, Action]:
    choices: dict[str, Action] = {}
    for choice in frame.cursor.get_choices(ctx=frame.context):
        choices[choice.get_content().replace("_", " ")] = choice
    return choices


def test_compound_conditions_and_effect_helpers() -> None:
    with RESOURCE_PATH.open(encoding="utf8") as handle:
        data = yaml.safe_load(handle)

    ledger = _build_ledger(data)

    frame = ledger.get_frame()
    initial_choices = _choices_by_text(frame)
    assert {
        "Call for help",
        "Inspect the courtyard",
        "Practice your swings",
    } == set(initial_choices)
    assert "Force the door open" not in initial_choices
    assert "Use the key" not in initial_choices

    training_choice = initial_choices["Practice your swings"]
    frame.resolve_choice(training_choice)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.graph.locals["player_strength"] == 6
    assert ledger.graph.locals["door_hint"] == "brute_force"
    assert ledger.graph.locals["has_key"] is False

    frame = ledger.get_frame()
    post_training_choices = _choices_by_text(frame)
    assert "Force the door open" in post_training_choices
    assert "Use the key" not in post_training_choices
    assert "Call for help" not in post_training_choices

    courtyard_choice = post_training_choices["Inspect the courtyard"]
    frame.resolve_choice(courtyard_choice)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    frame = ledger.get_frame()
    assert ledger.graph.locals["visited_garden"] is True
    courtyard_choices = _choices_by_text(frame)
    search_choice = courtyard_choices["Search the ivy"]
    frame.resolve_choice(search_choice)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    item = ledger.graph.find_one(label="ancient_key")
    assert isinstance(item, Item)
    assert item.has_tags(Item.ACQUIRED_TAG)
    assert ledger.graph.locals["has_key"] is True

    frame = ledger.get_frame()
    final_choices = _choices_by_text(frame)
    assert "Use the key" in final_choices
    assert "Force the door open" not in final_choices
    assert "Call for help" not in final_choices

    assert ledger.graph.locals["player_strength"] == 6
