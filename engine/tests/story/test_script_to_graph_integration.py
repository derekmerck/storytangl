from __future__ import annotations

from tangl.core import StreamRegistry
from tangl.core.graph import Edge, Graph, Node
from tangl.story.concepts.actor import Actor
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.ledger import Ledger


class NarrativeBlock(Node):
    content: str | None = None


class NarrativeAction(Edge):
    text: str | None = None


NarrativeBlock.model_rebuild()
NarrativeAction.model_rebuild()
Actor.model_rebuild()


def _build_world(script_data: dict) -> World:
    World.clear_instances()
    script_manager = ScriptManager.from_data(script_data)
    world = World(
        label="integration_world",
        script_manager=script_manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=script_manager.get_story_metadata(),
    )
    world.domain_manager.register_class("NarrativeBlock", NarrativeBlock)
    world.domain_manager.register_class("NarrativeAction", NarrativeAction)
    return world


def _make_crossroads_script() -> dict:
    return {
        "label": "crossroads_demo",
        "metadata": {
            "title": "The Crossroads",
            "author": "Test Author",
        },
        "scenes": {
            "crossroads": {
                "blocks": {
                    "start": {
                        "block_cls": "NarrativeBlock",
                        "content": "You stand at a crossroads.",
                        "actions": [
                            {
                                "obj_cls": "NarrativeAction",
                                "text": "Take the left path",
                                "successor": "garden.entrance",
                            },
                            {
                                "obj_cls": "NarrativeAction",
                                "text": "Take the right path",
                                "successor": "cave.entrance",
                            },
                        ],
                    }
                }
            },
            "garden": {
                "blocks": {
                    "entrance": {
                        "block_cls": "NarrativeBlock",
                        "content": "A peaceful garden.",
                    }
                }
            },
            "cave": {
                "blocks": {
                    "entrance": {
                        "block_cls": "NarrativeBlock",
                        "content": "A dark cave.",
                    }
                }
            },
        },
    }


def test_complete_story_creation() -> None:
    world = _build_world(_make_crossroads_script())
    story = world.create_story("test_story")

    assert story.initial_cursor_id is not None
    start_node = story.get(story.initial_cursor_id)
    assert isinstance(start_node, NarrativeBlock)
    assert start_node.label == "start"
    assert start_node.content == "You stand at a crossroads."

    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="test_story",
    )
    ledger.push_snapshot()
    ledger.init_cursor()

    assert ledger.cursor_id == story.initial_cursor_id
    # todo: I think that actually it _should_ be at sink (as it is), b/c this is a terminal choice and it autofollows to the sink?  idk?
    frame = ledger.get_frame()
    assert frame.cursor.label == "start", f"cursor should be 'start' ({frame.cursor.get_label()})"

    actions = [
        edge
        for edge in story.find_edges(source_id=frame.cursor_id)
        if getattr(edge, "trigger_phase", None) is None
    ]
    assert {action.label for action in actions} == {
        "Take_the_left_path",
        "Take_the_right_path",
    }

    left_action = next(action for action in actions if action.label == "Take_the_left_path")

    frame.follow_edge(left_action)

    destination = story.get(left_action.destination_id)
    assert isinstance(destination, NarrativeBlock)
    assert destination.content == "A peaceful garden."
    assert frame.cursor_id == destination.uid


def test_with_actors() -> None:
    script_data = _make_crossroads_script()
    script_data["actors"] = {
        "alice": {
            "obj_cls": "tangl.story.concepts.actor.actor.Actor",
            "name": "Alice",
        },
        "bob": {
            "obj_cls": "tangl.story.concepts.actor.actor.Actor",
            "name": "Bob",
        },
    }

    world = _build_world(script_data)
    story = world.create_story("test_story")

    alice = story.find_one(label="alice")
    assert isinstance(alice, Actor)
    assert alice.name == "Alice"

    bob = story.find_one(label="bob")
    assert isinstance(bob, Actor)
    assert bob.name == "Bob"


def test_with_custom_class() -> None:
    class Elf(Actor):
        elf_magic: int = 100

    Elf.model_rebuild()

    script_data = _make_crossroads_script()
    script_data["actors"] = {
        "legolas": {
            "obj_cls": "Elf",
            "name": "Legolas",
            "elf_magic": 200,
        }
    }

    world = _build_world(script_data)
    world.domain_manager.register_class("Elf", Elf)

    story = world.create_story("test_story")
    legolas = story.find_one(label="legolas")

    assert isinstance(legolas, Elf)
    assert legolas.elf_magic == 200
