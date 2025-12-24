"""Role and setting dependency wiring across world creation modes."""

from __future__ import annotations

from __future__ import annotations

import pytest

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.vm.provision import Dependency


@pytest.fixture(autouse=True)
def clear_world():
    """Reset world singleton across tests."""

    World.clear_instances()
    yield
    World.clear_instances()


def _build_world(script_data: dict) -> World:
    script = StoryScript.model_validate(script_data)
    manager = ScriptManager.from_master_script(master_script=script)
    return World(
        label="roles_test",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def _role_script(policy: str) -> dict:
    """Construct script data for role wiring assertions."""

    return {
        "label": "roles_test",
        "metadata": {"title": "Roles Test", "author": "Tests"},
        "templates": {
            "bartender": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "label": "bartender",
                "name": "Bartender",
            }
        },
        "scenes": {
            "tavern": {
                "label": "tavern",
                "blocks": {
                    "main": {
                        "label": "main",
                        "content": "Tavern main room",
                        "roles": [
                            {
                                "label": "barkeep",
                                "actor_template_ref": "bartender",
                                "policy": policy,
                                "hard": True,
                            }
                        ],
                    }
                },
            }
        },
    }


def test_lazy_mode_roles_create_open_dependencies():
    """Lazy mode should wire dependencies but leave them open."""

    world = _build_world(_role_script(policy="ANY"))
    graph = world.create_story("test", mode="lazy")

    main_block = graph.find_node(label="main")
    assert main_block is not None

    dependencies = list(graph.find_edges(source=main_block, is_instance=Dependency))
    barkeep_deps = [edge for edge in dependencies if edge.label == "barkeep"]
    assert len(barkeep_deps) == 1

    requirement = barkeep_deps[0].requirement
    assert not requirement.satisfied
    assert requirement.provider is None


def test_full_mode_roles_resolved(world_with_roles):
    """Full mode should eagerly provision role providers."""

    graph = world_with_roles.create_story("test", mode="full")
    main_block = graph.find_node(label="main")
    dependencies = list(graph.find_edges(source=main_block, is_instance=Dependency))
    barkeep_dep = [edge for edge in dependencies if edge.label == "barkeep"][0]

    assert barkeep_dep.requirement.satisfied
    assert barkeep_dep.requirement.provider is not None


@pytest.fixture
def world_with_roles():
    """World fixture shared across mode tests."""

    return _build_world(_role_script(policy="ANY"))


def test_hybrid_mode_roles_open(world_with_roles):
    """Hybrid mode should materialize dependencies but leave them unresolved."""

    graph = world_with_roles.create_story("test", mode="hybrid")
    main_block = graph.find_node(label="main")
    dependencies = list(graph.find_edges(source=main_block, is_instance=Dependency))
    barkeep_dep = [edge for edge in dependencies if edge.label == "barkeep"][0]

    assert not barkeep_dep.requirement.satisfied
    assert barkeep_dep.requirement.provider is None


def test_policy_any_reuses_actor_instance():
    """policy=ANY should reuse an existing provider when available."""

    world = _build_world(
        {
            "label": "shared_actor",
            "metadata": {"title": "Shared", "author": "Tests"},
            "templates": {
                "guard": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "guard",
                    "name": "Guard",
                }
            },
            "scenes": {
                "castle": {
                    "label": "castle",
                    "blocks": {
                        "gate": {
                            "label": "gate",
                            "content": "Castle gate",
                            "roles": [
                                {
                                    "label": "sentry",
                                    "actor_template_ref": "guard",
                                    "policy": "ANY",
                                }
                            ],
                        },
                        "courtyard": {
                            "label": "courtyard",
                            "content": "Castle courtyard",
                            "roles": [
                                {
                                    "label": "guard",
                                    "actor_template_ref": "guard",
                                    "policy": "ANY",
                                }
                            ],
                        },
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="full")
    gate = graph.find_node(label="gate")
    courtyard = graph.find_node(label="courtyard")

    gate_dep = list(graph.find_edges(source=gate, is_instance=Dependency))[0]
    courtyard_dep = list(graph.find_edges(source=courtyard, is_instance=Dependency))[0]

    assert gate_dep.requirement.provider is not None
    assert gate_dep.requirement.provider is courtyard_dep.requirement.provider


def test_policy_create_makes_unique_instances():
    """policy=CREATE should materialize separate providers."""

    world = _build_world(
        {
            "label": "unique_actors",
            "metadata": {"title": "Unique", "author": "Tests"},
            "templates": {
                "guard": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "guard",
                    "name": "Guard",
                }
            },
            "scenes": {
                "castle": {
                    "label": "castle",
                    "blocks": {
                        "gate": {
                            "label": "gate",
                            "content": "Castle gate",
                            "roles": [
                                {
                                    "label": "sentry",
                                    "actor_template_ref": "guard",
                                    "policy": "CREATE",
                                }
                            ],
                        },
                        "courtyard": {
                            "label": "courtyard",
                            "content": "Castle courtyard",
                            "roles": [
                                {
                                    "label": "guard",
                                    "actor_template_ref": "guard",
                                    "policy": "CREATE",
                                }
                            ],
                        },
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="full")
    gate = graph.find_node(label="gate")
    courtyard = graph.find_node(label="courtyard")

    gate_dep = list(graph.find_edges(source=gate, is_instance=Dependency))[0]
    courtyard_dep = list(graph.find_edges(source=courtyard, is_instance=Dependency))[0]

    assert gate_dep.requirement.provider is not None
    assert courtyard_dep.requirement.provider is not None
    assert gate_dep.requirement.provider is not courtyard_dep.requirement.provider

