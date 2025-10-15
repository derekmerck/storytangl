from __future__ import annotations

from pathlib import Path

import yaml

from tangl.core.graph.graph import Graph as StoryGraph
from tangl.story.concepts.actor import Actor
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.frame import Frame


Actor.model_rebuild(_types_namespace={"Graph": StoryGraph})


def test_load_demo_script() -> None:
    World.clear_instances()
    script_path = Path(__file__).resolve().parent.parent / "resources" / "demo_script.yaml"
    data = yaml.safe_load(script_path.read_text())

    script_manager = ScriptManager.from_data(data)
    world = World(label="demo_world", script_manager=script_manager)

    story = world.create_story("demo_story")

    assert isinstance(story.cursor, Frame)
    frame = story.cursor
    assert frame.cursor.label == "start"

    # todo: this does _not_ test that an initial journal entry was created at the cursor

    outgoing = list(
        story.find_edges(source_id=frame.cursor_id, trigger_phase=None)
    )
    labels = {edge.label for edge in outgoing}
    expected_labels = {text.replace(" ", "_") for text in ("Take the left path", "Take the right path")}
    assert labels == expected_labels

    left_edge = next(edge for edge in outgoing if edge.label.endswith("left_path"))
    frame.follow_edge(left_edge)

    assert frame.cursor.label == "entrance"

    next_edges = list(story.find_edges(source_id=frame.cursor_id))
    assert any(
        story.get(edge.destination_id).label == "finale" for edge in next_edges
    )

    guide = story.find_one(label="guide")
    assert guide is not None
    assert guide.name == "The Guide"
    assert guide.has_tags({"npc", "helpful"})
