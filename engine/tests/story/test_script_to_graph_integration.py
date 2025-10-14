from __future__ import annotations

from tangl.compiler.script_manager import ScriptManager
from tangl.core.graph import Edge, Node, Graph
from tangl.story.concepts.actor import Actor
from tangl.story.fabula.world import World
from tangl.vm.frame import Frame


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
    world = World(label="integration_world", script_manager=script_manager)
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

    assert isinstance(story.cursor, Frame)
    frame = story.cursor

    assert frame.cursor.label == "start"
    assert isinstance(frame.cursor, NarrativeBlock)
    assert frame.cursor.content == "You stand at a crossroads."

    actions = [
        edge
        for edge in story.find_edges(source_id=frame.cursor_id)
        if getattr(edge, "text", None)
    ]
    assert {action.text for action in actions} == {
        "Take the left path",
        "Take the right path",
    }

    left_action = next(action for action in actions if action.text == "Take the left path")

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
