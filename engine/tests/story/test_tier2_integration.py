from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from tangl.core import BaseFragment, StreamRegistry
from tangl.story.concepts.actor.actor import Actor
from tangl.story.concepts.item import Item
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger


def _load_tier2_ledger(resources_dir: Path) -> tuple[Ledger, Frame]:
    script_path = resources_dir / "tier2_demo.yaml"
    data = yaml.safe_load(script_path.read_text())

    World.clear_instances()
    script_manager = ScriptManager.from_data(data)
    world = World(
        label="tier2_demo_world",
        script_manager=script_manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=script_manager.get_story_metadata(),
    )
    story = world.create_story("tier2_demo_story")

    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="tier2_demo_ledger",
    )
    ledger.push_snapshot()
    ledger.init_cursor()
    frame = ledger.get_frame()
    return ledger, frame


def _choice_labels(choices: Iterable[BaseFragment]) -> set[str]:
    return {choice.get_content().replace("_", " ") for choice in choices}


def _choose_action(ledger: Ledger, frame: Frame, choice_text: str) -> Frame:
    choices = frame.cursor.get_choices(ctx=frame.context)
    labels = _choice_labels(choices)
    assert choice_text in labels, f"Expected {choice_text} in choices {labels}"

    choice = next(choice for choice in choices if choice.get_content().replace("_", " ") == choice_text)
    frame.resolve_choice(choice)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step
    return frame


def test_tier2_complete_walkthrough(resources_dir: Path) -> None:
    ledger, frame = _load_tier2_ledger(resources_dir)

    assert frame.cursor.label == "start"
    companion = next(concept for concept in frame.cursor.get_concepts() if concept.label == "companion")
    assert isinstance(companion, Actor)
    assert ledger.graph.locals["companion_trust"] == 0

    frame = _choose_action(ledger, frame, "Talk to Aria")
    assert ledger.graph.locals["companion_trust"] >= 2

    frame = _choose_action(ledger, frame, "Request her help")
    assert ledger.graph.locals["companion_trust"] >= 4
    assert frame.cursor.label == "start"

    trail_edge = next(
        edge
        for edge in ledger.graph.find_edges(source_id=frame.cursor.uid)
        if getattr(ledger.graph.get(edge.destination_id), "label", None) == "trail"
    )
    frame.follow_edge(trail_edge)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step
    frame = ledger.get_frame()
    assert frame.cursor.label == "trail"

    trail_choices = _choice_labels(frame.cursor.get_choices(ctx=frame.context))
    assert "Search for the map" in trail_choices

    frame = _choose_action(ledger, frame, "Search for the map")
    assert frame.cursor.label == "entrance"
    assert Item.has_item("map", graph=ledger.graph)
    assert ledger.graph.locals["has_map"] is True
    assert ledger.graph.locals["visited_shrine"] is True

    entrance_choices = _choice_labels(frame.cursor.get_choices(ctx=frame.context))
    assert "Take the crystal" not in entrance_choices
    assert ledger.graph.locals["companion_trust"] < 5

    frame = _choose_action(ledger, frame, "Ask Aria to translate the runes")
    assert frame.cursor.label == "entrance"
    assert ledger.graph.locals["companion_trust"] >= 5

    frame = _choose_action(ledger, frame, "Take the crystal")
    assert Item.has_item("crystal", graph=ledger.graph)
    assert ledger.graph.locals["has_crystal"] is True

    frame = _choose_action(ledger, frame, "Return triumphantly")
    finale_frame = ledger.get_frame()
    assert finale_frame.cursor.label in {"finale", "shrine_SINK"}
