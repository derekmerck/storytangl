"""Compiler/materializer requirement-path metadata tests for story38."""

from __future__ import annotations

from tangl.core38 import Selector
from tangl.story38 import InitMode, World38
from tangl.story38.episode import Action
from tangl.vm38 import Dependency


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
                        "actions": [{"text": "Go", "successor": "missing"}],
                    },
                }
            }
        },
    }
    world = World38.from_script_data(script_data=script)
    result = world.create_story("meta_story", init_mode=InitMode.LAZY)
    graph = result.graph

    action = next(graph.find_edges(Selector(has_kind=Action)), None)
    assert action is not None
    dep = _destination_dependency(graph, action)

    assert dep.requirement.authored_path == "missing"
    assert dep.requirement.is_qualified is False
    assert (dep.requirement.__pydantic_extra__ or {}).get("has_identifier") == "scene.missing"


def test_qualified_successor_preserves_authored_path_and_marks_qualified() -> None:
    script = {
        "label": "meta_world_qualified",
        "metadata": {"title": "Meta", "author": "Tests", "start_at": "scene.start"},
        "scenes": {
            "scene": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "scene.missing"}],
                    },
                }
            }
        },
    }
    world = World38.from_script_data(script_data=script)
    result = world.create_story("meta_story_qualified", init_mode=InitMode.LAZY)
    graph = result.graph

    action = next(graph.find_edges(Selector(has_kind=Action)), None)
    assert action is not None
    dep = _destination_dependency(graph, action)

    assert dep.requirement.authored_path == "scene.missing"
    assert dep.requirement.is_qualified is True
    assert (dep.requirement.__pydantic_extra__ or {}).get("has_identifier") == "scene.missing"
