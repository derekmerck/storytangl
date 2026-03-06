"""Compiler/materializer requirement-path metadata tests for story38."""

from __future__ import annotations

from tangl.core import Selector
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.vm import Dependency


def _destination_dependency(graph, action: Action) -> Dependency:
    dep = next(
        graph.find_edges(
            Selector(has_kind=Dependency, predecessor=action, label="destination")
        ),
        None,
    )
    assert dep is not None
    return dep


def test_bare_successor_preserves_authored_path_and_marks_unqualified() -> None:
    script = {
        "label": "meta_world",
        "metadata": {"title": "Meta", "author": "Tests", "start_at": "scene.start"},
        "scenes": {
            "scene": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "end"}],
                    },
                    "end": {"content": "End"},
                }
            }
        },
    }
    world = World.from_script_data(script_data=script)
    result = world.create_story("meta_story", init_mode=InitMode.LAZY)
    graph = result.graph

    action = next(graph.find_edges(Selector(has_kind=Action)), None)
    assert action is not None
    dep = _destination_dependency(graph, action)

    assert dep.requirement.authored_path == "end"
    assert dep.requirement.is_qualified is False
    assert dep.requirement.is_absolute is False
    assert (dep.requirement.__pydantic_extra__ or {}).get("has_identifier") == "scene.end"


def test_qualified_successor_preserves_authored_path_and_marks_qualified() -> None:
    script = {
        "label": "meta_world_qualified",
        "metadata": {"title": "Meta", "author": "Tests", "start_at": "scene.start"},
        "scenes": {
            "scene": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene.end"}],
                    },
                    "end": {"content": "End"},
                }
            }
        },
    }
    world = World.from_script_data(script_data=script)
    result = world.create_story("meta_story_qualified", init_mode=InitMode.LAZY)
    graph = result.graph

    action = next(graph.find_edges(Selector(has_kind=Action)), None)
    assert action is not None
    dep = _destination_dependency(graph, action)

    assert dep.requirement.authored_path == "scene.end"
    assert dep.requirement.is_qualified is True
    assert dep.requirement.is_absolute is False
    assert (dep.requirement.__pydantic_extra__ or {}).get("has_identifier") == "scene.end"


def test_cross_scene_bare_successor_marks_absolute() -> None:
    script = {
        "label": "meta_world_cross_scene",
        "metadata": {"title": "Meta", "author": "Tests", "start_at": "scene1.start"},
        "scenes": {
            "scene1": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene2"}],
                    },
                }
            },
            "scene2": {
                "blocks": {
                    "entry": {"content": "Entry"},
                }
            },
        },
    }
    world = World.from_script_data(script_data=script)
    result = world.create_story("meta_story_cross_scene", init_mode=InitMode.LAZY)
    graph = result.graph

    action = next(graph.find_edges(Selector(has_kind=Action)), None)
    assert action is not None
    dep = _destination_dependency(graph, action)

    assert dep.requirement.authored_path == "scene2"
    assert dep.requirement.is_qualified is False
    assert dep.requirement.is_absolute is True
    assert (dep.requirement.__pydantic_extra__ or {}).get("has_identifier") == "scene2"
