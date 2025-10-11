from __future__ import annotations

from tangl.compiler.script_manager import ScriptManager
from tangl.core.graph.edge import Edge
from tangl.core.graph.graph import Graph
from tangl.core.graph.node import Node
from tangl.story.story_domain.world import World
from tangl.story.reference_domain.block import SimpleBlock as ReferenceBlock
from tangl.vm.frame import ChoiceEdge


class SimpleBlock(Node):
    content: str | None = None


class SimpleAction(Edge):
    text: str | None = None


def _make_world(script_data: dict) -> World:
    World.clear_instances()
    script_manager = ScriptManager.from_data(script_data)
    world = World(label="test_world", script_manager=script_manager)
    world.domain_manager.register_class("SimpleBlock", SimpleBlock)
    world.domain_manager.register_class("SimpleAction", SimpleAction)
    return world


def _base_script() -> dict:
    return {
        "label": "test_script",
        "metadata": {"title": "Test", "author": "Tester"},
        "actors": {
            "hero": {"obj_cls": "tangl.core.graph.node.Node"},
        },
        "locations": {
            "town": {"obj_cls": "tangl.core.graph.node.Node"},
        },
    }


def test_build_actors_populates_graph() -> None:
    script = _base_script()
    script["scenes"] = {"intro": {"blocks": {"start": {}}}}

    world = _make_world(script)
    graph = Graph(label="story")

    actor_map = world._build_actors(graph)

    assert set(actor_map) == {"hero"}
    assert len(graph.data) == 1


def test_build_blocks_collects_action_scripts() -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "SimpleBlock",
                    "content": "Hello",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Continue",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "SimpleBlock"},
            }
        }
    }

    world = _make_world(script)
    graph = Graph(label="story")

    block_map, action_scripts = world._build_blocks(graph)

    assert set(block_map) == {"intro.start", "intro.next"}
    assert "actions" in action_scripts["intro.start"]
    assert action_scripts["intro.start"]["actions"][0]["text"] == "Continue"


def test_build_action_edges_wires_successors() -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "SimpleBlock",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Continue",
                            "successor": "next",
                        },
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Outro",
                            "successor": "outro",
                        },
                    ],
                },
                "next": {"obj_cls": "SimpleBlock"},
            }
        },
        "outro": {
            "blocks": {
                "end": {"obj_cls": "SimpleBlock"},
            }
        },
    }

    world = _make_world(script)
    graph = Graph(label="story")
    block_map, action_scripts = world._build_blocks(graph)

    world._build_action_edges(graph, block_map, action_scripts)

    start_uid = block_map["intro.start"]
    edges = list(graph.find_edges(source_id=start_uid))

    assert len(edges) == 2
    labels = {edge.label for edge in edges}
    assert labels == {"Continue", "Outro"}

    destinations = {edge.destination_id for edge in edges}
    assert destinations == {
        block_map["intro.next"],
        block_map["outro.end"],
    }


def test_create_story_full_returns_populated_graph() -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "SimpleBlock",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Continue",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "SimpleBlock"},
            }
        }
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    assert isinstance(story_graph, Graph)
    # actors, locations, and two blocks
    assert len(story_graph.data) >= 4

    edges = list(story_graph.find_edges())
    assert edges and edges[0].destination_id in story_graph.data
    assert story_graph.cursor is not None
    assert story_graph.cursor.cursor.label in {"start", "next"}


def test_create_story_full_uses_metadata_start_at() -> None:
    script = _base_script()
    script["metadata"]["start_at"] = "intro.next"
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "SimpleBlock",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Go",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "SimpleBlock"},
            }
        }
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    assert story_graph.cursor.cursor.label == "next"


def test_create_story_full_defaults_to_first_block() -> None:
    script = _base_script()
    script["metadata"].pop("start_at", None)
    script["scenes"] = {
        "intro": {
            "blocks": [
                {"label": "start", "obj_cls": "SimpleBlock"},
                {"label": "next", "obj_cls": "SimpleBlock"},
            ]
        }
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    assert story_graph.cursor.cursor.label == "start"


def test_story_creation_uses_default_classes_when_obj_cls_missing() -> None:
    script = {
        "label": "default_class_script",
        "metadata": {"title": "Defaults", "author": "Tester"},
        "actors": {"guide": {"name": "Guide"}},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Welcome",
                        "actions": [
                            {
                                "text": "Next",
                                "successor": "intro.end",
                            }
                        ],
                    },
                    "end": {
                        "content": "Goodbye",
                    },
                }
            }
        },
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    start_block = story_graph.find_one(label="start")
    assert isinstance(start_block, ReferenceBlock)
    assert start_block.content == "Welcome"

    edges = list(story_graph.find_edges(source_id=start_block.uid))
    assert edges
    assert any(isinstance(edge, ChoiceEdge) for edge in edges)
