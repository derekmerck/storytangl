from __future__ import annotations

from tangl.core.graph.graph import Graph
from tangl.core.graph.node import Node
from tangl.story.concepts.actor.role import Role
from tangl.story.concepts.location.setting import Setting
from tangl.story.episode.block import Block as ReferenceBlock
from tangl.vm.frame import ChoiceEdge

from conftest import _base_script, _make_world


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
                    "obj_cls": "Block",
                    "content": "Hello",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Continue",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "Block"},
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
                    "obj_cls": "Block",
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
                "next": {"obj_cls": "Block"},
            }
        },
        "outro": {
            "blocks": {
                "end": {"obj_cls": "Block"},
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
                    "obj_cls": "Block",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Continue",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "Block"},
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
    assert story_graph.initial_cursor_id is not None
    start_node = story_graph.get(story_graph.initial_cursor_id)
    assert start_node is not None
    assert start_node.label in {"start", "next"}


def test_create_story_full_uses_metadata_start_at() -> None:
    script = _base_script()
    script["metadata"]["start_at"] = "intro.next"
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "Block",
                    "actions": [
                        {
                            "obj_cls": "SimpleAction",
                            "text": "Go",
                            "successor": "next",
                        }
                    ],
                },
                "next": {"obj_cls": "Block"},
            }
        }
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    assert story_graph.initial_cursor_id is not None
    start_node = story_graph.get(story_graph.initial_cursor_id)
    assert start_node is not None
    assert start_node.label == "next"


def test_create_story_full_defaults_to_first_block() -> None:
    script = _base_script()
    script["metadata"].pop("start_at", None)
    script["scenes"] = {
        "intro": {
            "blocks": [
                {"label": "start", "obj_cls": "Block"},
                {"label": "next", "obj_cls": "Block"},
            ]
        }
    }

    world = _make_world(script)
    story_graph = world.create_story("story")

    assert story_graph.initial_cursor_id is not None
    start_node = story_graph.get(story_graph.initial_cursor_id)
    assert start_node is not None
    assert start_node.label == "start"


def test_build_scenes_wires_role_and_setting_dependencies() -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "Block",
                    "roles": {"hero_role": {"actor_ref": "hero"}},
                    "settings": {"home": {"location_ref": "town"}},
                },
            },
            "roles": {"leader": {"actor_ref": "hero"}},
            "settings": {"meeting_hall": {"location_ref": "town"}},
        }
    }

    world = _make_world(script)
    graph = Graph(label="story")

    actor_map = world._build_actors(graph)
    location_map = world._build_locations(graph)
    block_map, _ = world._build_blocks(graph)
    scene_map = world._build_scenes(
        graph,
        block_map,
        actor_map=actor_map,
        location_map=location_map,
    )

    scene_uid = scene_map["intro"]
    scene = graph.get(scene_uid)
    assert scene is not None

    hero_uid = actor_map["hero"]

    scene_roles = list(graph.find_edges(source_id=scene_uid, is_instance=Role))
    assert len(scene_roles) == 1
    assert scene_roles[0].label == "leader"
    assert scene_roles[0].destination_id == hero_uid

    scene_settings = list(graph.find_edges(source_id=scene_uid, is_instance=Setting))
    assert len(scene_settings) == 1
    assert scene_settings[0].label == "meeting_hall"
    assert scene_settings[0].destination_id == location_map["town"]

    block = graph.get(block_map["intro.start"])
    assert block is not None

    block_roles = list(graph.find_edges(source=block, is_instance=Role))
    assert len(block_roles) == 1
    assert block_roles[0].label == "hero_role"
    assert block_roles[0].destination_id == hero_uid

    block_settings = list(graph.find_edges(source=block, is_instance=Setting))
    assert len(block_settings) == 1
    assert block_settings[0].label == "home"
    assert block_settings[0].destination_id == location_map["town"]


def test_missing_role_and_setting_targets_warn(caplog) -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "Block",
                }
            },
            "roles": {"mystery": {"actor_ref": "unknown_actor"}},
            "settings": {"void": {"location_ref": "unknown_location"}},
        }
    }

    world = _make_world(script)
    graph = Graph(label="story")

    actor_map = world._build_actors(graph)
    location_map = world._build_locations(graph)
    block_map, _ = world._build_blocks(graph)

    with caplog.at_level("WARNING"):
        scene_map = world._build_scenes(
            graph,
            block_map,
            actor_map=actor_map,
            location_map=location_map,
        )

    warnings = caplog.text
    assert "unknown actor" in warnings
    assert "unknown location" in warnings

    scene_uid = scene_map["intro"]
    scene = graph.get(scene_uid)
    assert scene is not None

    role = graph.find_one(source_id=scene_uid, is_instance=Role)
    assert role is not None
    assert role.destination is None

    setting = graph.find_one(source_id=scene_uid, is_instance=Setting)
    assert setting is not None
    assert setting.destination is None


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


def test_build_blocks_respects_custom_block_class() -> None:
    class NarrativeBlock(Node):
        content: str | None = None

    NarrativeBlock.model_rebuild()

    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "NarrativeBlock",
                    "content": "Custom",
                }
            }
        }
    }

    world = _make_world(script)
    world.domain_manager.register_class("NarrativeBlock", NarrativeBlock)

    graph = Graph(label="story")
    block_map, _ = world._build_blocks(graph)

    block_uid = block_map["intro.start"]
    block = graph.get(block_uid)

    assert isinstance(block, NarrativeBlock)
    assert block.content == "Custom"


def test_action_edges_set_trigger_phase_for_auto_edges() -> None:
    script = _base_script()
    script["scenes"] = {
        "intro": {
            "blocks": {
                "start": {
                    "obj_cls": "Block",
                    "continues": [
                        {
                            "successor": "intro.end",
                        }
                    ],
                },
                "end": {"obj_cls": "Block"},
            }
        }
    }

    world = _make_world(script)
    graph = Graph(label="story")

    block_map, action_scripts = world._build_blocks(graph)
    world._build_action_edges(graph, block_map, action_scripts)

    start_uid = block_map["intro.start"]
    edges = list(graph.find_edges(source_id=start_uid))

    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, ChoiceEdge)
    from tangl.vm import ResolutionPhase as P

    assert edge.trigger_phase == P.POSTREQS
