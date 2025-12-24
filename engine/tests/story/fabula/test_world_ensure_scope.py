from __future__ import annotations

import pytest

from tangl.core.graph.subgraph import Subgraph
from tangl.ir.story_ir import StoryScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.story_graph import StoryGraph


@pytest.fixture
def minimal_world():
    """World with a single scene template and block."""

    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test", "author": "Tests"},
        "templates": {
            "village": {
                "obj_cls": "tangl.core.graph.Subgraph",
                "label": "village",
            }
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "start": {
                        "label": "start",
                        "obj_cls": "tangl.story.episode.block.Block",
                        "content": "Village start",
                    }
                },
            }
        },
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager.from_master_script(master_script=script)

    world = World(
        label="test_world",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    yield world
    World.clear_instances()


def test_ensure_scope_returns_none_for_global_scope(minimal_world: World) -> None:
    graph = StoryGraph(label="test", world=minimal_world)

    result = minimal_world.ensure_scope(scope=None, graph=graph)

    assert result is None


def test_ensure_scope_returns_none_for_selector_without_parent(
    minimal_world: World,
) -> None:
    graph = StoryGraph(label="test", world=minimal_world)
    scope = ScopeSelector()

    result = minimal_world.ensure_scope(scope=scope, graph=graph)

    assert result is None


def test_ensure_scope_reuses_existing_scene(minimal_world: World) -> None:
    graph = StoryGraph(label="test", world=minimal_world)

    existing_scene = graph.add_subgraph(label="village")

    scope = {"has_path": "village.*"}
    result = minimal_world.ensure_scope(scope=scope, graph=graph)

    assert result is existing_scene
    assert len(list(graph.subgraphs)) == 1


def test_ensure_scope_creates_scene_from_template(minimal_world: World) -> None:
    graph = StoryGraph(label="test", world=minimal_world)
    scope = {"has_path": "village.*"}

    created = minimal_world.ensure_scope(scope=scope, graph=graph)

    assert isinstance(created, Subgraph)
    assert created.label == "village"
    assert created in graph.subgraphs
    assert graph.find_subgraph(label="village") is created


def test_ensure_scope_idempotent(minimal_world: World) -> None:
    graph = StoryGraph(label="test", world=minimal_world)
    scope = {"has_path": "village.*"}

    first = minimal_world.ensure_scope(scope=scope, graph=graph)
    second = minimal_world.ensure_scope(scope=scope, graph=graph)

    assert first is second
    assert len(list(graph.subgraphs)) == 1


def test_ensure_scope_errors_when_template_missing(minimal_world: World) -> None:
    graph = StoryGraph(label="test", world=minimal_world)
    scope = {"has_path": "missing.*"}

    with pytest.raises(ValueError, match="no template found"):
        minimal_world.ensure_scope(scope=scope, graph=graph)


def test_ensure_scope_recursively_creates_parent_hierarchy() -> None:
    World.clear_instances()

    script_data = {
        "label": "hierarchical",
        "metadata": {"title": "Test", "author": "Tests"},
        "templates": {
            "chapter1": {
                "obj_cls": "tangl.core.graph.Subgraph",
                "label": "chapter1",
            },
            "village": {
                "obj_cls": "tangl.core.graph.Subgraph",
                "label": "village",
                "scope": {"parent_label": "chapter1"},
            },
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager.from_master_script(master_script=script)
    world = World(
        label="hierarchical",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    try:
        graph = StoryGraph(label="test", world=world)
        scope = {"has_path": "village.*"}

        created = world.ensure_scope(scope=scope, graph=graph)

        chapter = graph.find_subgraph(label="chapter1")
        village = graph.find_subgraph(label="village")

        assert created is village
        assert chapter is not None
        assert village is not None
        assert village.parent is chapter
    finally:
        World.clear_instances()
