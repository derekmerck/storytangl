"""Tests for role and setting dependency wiring during materialization."""

from __future__ import annotations

import pytest

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.story_graph import StoryGraph
from tangl.vm.provision import Dependency, ProvisioningPolicy


@pytest.fixture(autouse=True)
def clear_world():
    """Reset the World singleton between tests."""

    World.clear_instances()
    yield
    World.clear_instances()


def _make_world(script_data: dict) -> World:
    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    return World(
        label="test",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def _lazy_graph(script_data: dict) -> StoryGraph:
    world = _make_world(script_data)
    return world.create_story("test", mode="lazy")


def test_block_with_roles_creates_dependency_edges():
    """Roles should become Dependency edges with correct requirement fields."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "tavern": {
                    "label": "tavern",
                    "blocks": {
                        "main": {
                            "label": "main",
                            "content": "Tavern scene",
                            "roles": [
                                {
                                    "label": "bartender",
                                    "actor_template_ref": "bartender_template",
                                    "hard": True,
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    main_block = graph.find_node(label="main")
    assert main_block is not None

    dependencies = list(graph.find_edges(source=main_block, is_instance=Dependency))
    role_deps = [edge for edge in dependencies if edge.label == "bartender"]
    assert len(role_deps) == 1

    requirement = role_deps[0].requirement
    assert requirement.template_ref == "bartender_template"
    assert requirement.hard_requirement is True


def test_block_with_settings_creates_dependency_edges():
    """Settings should become Dependency edges for locations."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "chapter1": {
                    "label": "chapter1",
                    "blocks": {
                        "start": {
                            "label": "start",
                            "content": "Start",
                            "settings": [
                                {
                                    "label": "location",
                                    "location_template_ref": "dark_forest",
                                    "hard": True,
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    start = graph.find_node(label="start")
    assert start is not None

    dependencies = list(graph.find_edges(source=start, is_instance=Dependency))
    setting_deps = [edge for edge in dependencies if edge.label == "location"]
    assert len(setting_deps) == 1
    assert setting_deps[0].requirement.template_ref == "dark_forest"


def test_role_with_actor_ref_creates_identifier():
    """Roles with an actor_ref should populate the requirement identifier."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "hero",
                                    "actor_ref": "protagonist",
                                    "policy": "ANY",
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    block = graph.find_node(label="block1")
    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    hero_deps = [edge for edge in dependencies if edge.label == "hero"]
    assert len(hero_deps) == 1

    requirement = hero_deps[0].requirement
    assert requirement.identifier == "protagonist"
    assert requirement.policy == ProvisioningPolicy.ANY


def test_role_with_criteria_creates_criteria():
    """Roles with criteria should forward them into the requirement."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "guard",
                                    "actor_criteria": {"archetype": "guard", "has_tags": {"armed"}},
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    block = graph.find_node(label="block1")
    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    guard_deps = [edge for edge in dependencies if edge.label == "guard"]
    assert len(guard_deps) == 1

    requirement = guard_deps[0].requirement
    assert requirement.criteria is not None
    assert requirement.criteria.get("archetype") == "guard"
    assert "armed" in requirement.criteria.get("has_tags", set())


def test_soft_requirement_marked_correctly():
    """Roles marked hard=False should become soft requirements."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "optional_npc",
                                    "actor_template_ref": "merchant",
                                    "hard": False,
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    block = graph.find_node(label="block1")
    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    npc_deps = [edge for edge in dependencies if edge.label == "optional_npc"]
    assert len(npc_deps) == 1
    assert npc_deps[0].requirement.hard_requirement is False


def test_multiple_roles_create_multiple_dependencies():
    """Multiple roles should create multiple Dependency edges."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {"label": "guard1", "actor_template_ref": "guard"},
                                {"label": "guard2", "actor_template_ref": "guard"},
                                {"label": "captain", "actor_template_ref": "captain"},
                            ],
                        }
                    },
                }
            },
        }
    )

    block = graph.find_node(label="block1")
    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))

    labels = {edge.label for edge in dependencies}
    assert {"guard1", "guard2", "captain"}.issubset(labels)


def test_policy_defaults_to_any():
    """Policy should default to ANY when not specified."""

    graph = _lazy_graph(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "guard",
                                    "actor_template_ref": "guard",
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    block = graph.find_node(label="block1")
    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    guard_deps = [edge for edge in dependencies if edge.label == "guard"]
    assert guard_deps
    assert guard_deps[0].requirement.policy == ProvisioningPolicy.ANY
