from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tangl.story.concepts.actor import Actor
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.ledger import Ledger
from tangl.core import StreamRegistry

@pytest.fixture(autouse=True)
def _clear_worlds():
    World.clear_instances()
    yield
    World.clear_instances()

def test_load_demo_script(resources_dir) -> None:
    script_path = resources_dir / "demo_script.yaml"
    data = yaml.safe_load(script_path.read_text())

    script_manager = ScriptManager.from_data(data)
    world = World(label="demo_world", script_manager=script_manager)

    story = world.create_story("demo_story")

    assert story.initial_cursor_id is not None
    start_node = story.get(story.initial_cursor_id)
    assert start_node is not None
    assert start_node.label == "start"

    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="demo_story"
    )
    ledger.init_cursor()
    frame = ledger.get_frame()
    assert frame.cursor.label == "start"

    # todo: this does _not_ test that an initial journal entry was created at the cursor

    outgoing = list(story.find_edges(source_id=frame.cursor_id))
    labels = {
        edge.label
        for edge in outgoing
        if getattr(edge, "trigger_phase", None) is None
    }
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

def test_load_linear_script(resources_dir) -> None:
    script_path = resources_dir / "linear_script.yaml"
    data = yaml.safe_load(script_path.read_text())

    script_manager = ScriptManager.from_data(data)
    world = World(label="linear_world", script_manager=script_manager)

    story = world.create_story("linear_story")

    assert story.initial_cursor_id is not None
    start_node = story.get(story.initial_cursor_id)
    assert start_node is not None
    assert start_node.label == "start"

    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="linear_story",
    )
    ledger.init_cursor()
    frame = ledger.get_frame()
    assert frame.cursor.label == "start"

    def get_blocks(_fragments):
        return list(filter(lambda f: f.fragment_type == "block", _fragments))

    def get_choices(_fragments):
        return list(filter(lambda f: f.fragment_type == "choice", _fragments))

    def render_step(step, _fragments):
        print(f"------- step {step} --------")
        print(get_blocks(fragments)[0].content)
        print('choices:')
        print([f"{i+1}. {f.content}" for i, f in enumerate(get_choices(fragments))])

    fragments = list( ledger.get_journal('step-0001') )
    render_step(1, fragments)

    choice_fragment = get_choices(fragments)[0]
    choice_id = choice_fragment.source_id
    choice = ledger.graph.get(choice_id)
    frame.follow_edge(choice)

    fragments = list( ledger.get_journal('step-0002') )
    render_step(2, fragments)

    choice_fragment = get_choices(fragments)[0]
    choice_id = choice_fragment.source_id
    choice = ledger.graph.get(choice_id)
    frame.follow_edge(choice)

    fragments = ledger.get_journal('step-0003')
    render_step(3, fragments)
