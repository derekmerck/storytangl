"""Integration tests validating Phase 4 role/setting wiring."""

from __future__ import annotations

import pytest

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.vm.provision import Dependency


@pytest.fixture(autouse=True)
def clear_world() -> None:
    """Ensure the World singleton does not leak between tests."""

    World.clear_instances()
    yield
    World.clear_instances()


def _build_world(script_data: dict) -> World:
    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    return World(
        label=script.label,
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def test_phase4_complete_story_with_roles_and_settings() -> None:
    """End-to-end validation of roles, settings, and successor wiring."""

    world = _build_world(
        {
            "label": "complete",
            "metadata": {"title": "Complete", "author": "Tests"},
            "templates": {
                "innkeeper": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "innkeeper",
                    "name": "Innkeeper",
                },
                "inn_interior": {
                    "obj_cls": "tangl.story.concepts.location.location.Location",
                    "label": "inn_interior",
                    "name": "Inn Interior",
                },
            },
            "scenes": {
                "inn": {
                    "label": "inn",
                    "blocks": {
                        "entrance": {
                            "label": "entrance",
                            "content": "You enter the inn",
                            "roles": [
                                {
                                    "label": "host",
                                    "actor_template_ref": "innkeeper",
                                    "policy": "ANY",
                                }
                            ],
                            "settings": [
                                {
                                    "label": "interior",
                                    "location_template_ref": "inn_interior",
                                }
                            ],
                            "actions": [
                                {
                                    "text": "Talk to innkeeper",
                                    "successor": "conversation",
                                }
                            ],
                        },
                        "conversation": {
                            "label": "conversation",
                            "content": "Innkeeper greets you",
                        },
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="full")
    entrance = graph.find_node(label="entrance")
    assert entrance is not None

    role_deps = [
        edge
        for edge in graph.find_edges(source=entrance, is_instance=Dependency)
        if edge.label == "host"
    ]
    assert len(role_deps) == 1
    assert role_deps[0].requirement.satisfied
    assert role_deps[0].requirement.provider is not None
    assert role_deps[0].requirement.provider.name == "Innkeeper"

    setting_deps = [
        edge
        for edge in graph.find_edges(source=entrance, is_instance=Dependency)
        if edge.label == "interior"
    ]
    assert len(setting_deps) == 1
    assert setting_deps[0].requirement.satisfied
    assert setting_deps[0].requirement.provider is not None
    assert setting_deps[0].requirement.provider.name == "Inn Interior"

    from tangl.story.episode.action import Action

    actions = list(entrance.edges_out(is_instance=Action))
    assert len(actions) == 1

    action_deps = list(graph.find_edges(source=actions[0], is_instance=Dependency))
    assert len(action_deps) == 1
    assert action_deps[0].requirement.identifier == "inn.conversation"


def test_phase4_script_to_graph_complete_translation() -> None:
    """Ensure scripts translate to graph nodes, dependencies, and actions."""

    world = _build_world(
        {
            "label": "translation_test",
            "metadata": {"title": "Translation", "author": "Tests"},
            "templates": {
                "guard": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "guard",
                },
                "merchant": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "merchant",
                },
                "plaza": {
                    "obj_cls": "tangl.story.concepts.location.location.Location",
                    "label": "plaza",
                },
            },
            "scenes": {
                "city": {
                    "label": "city",
                    "blocks": {
                        "gate": {
                            "label": "gate",
                            "content": "City gate",
                            "roles": [
                                {
                                    "label": "sentry",
                                    "actor_template_ref": "guard",
                                    "hard": True,
                                },
                                {
                                    "label": "visitor",
                                    "actor_template_ref": "merchant",
                                    "hard": False,
                                },
                            ],
                            "settings": [
                                {
                                    "label": "location",
                                    "location_template_ref": "plaza",
                                }
                            ],
                            "actions": [
                                {"text": "Enter city", "successor": "market"}
                            ],
                        },
                        "market": {
                            "label": "market",
                            "content": "City market",
                        },
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="lazy")
    gate = graph.find_node(label="gate")
    assert gate is not None

    gate_deps = list(graph.find_edges(source=gate, is_instance=Dependency))
    assert len(gate_deps) == 3

    labels = {edge.label for edge in gate_deps}
    assert labels == {"sentry", "visitor", "location"}

    from tangl.story.episode.action import Action

    actions = list(gate.edges_out(is_instance=Action))
    assert len(actions) == 1

    action_deps = list(graph.find_edges(source=actions[0], is_instance=Dependency))
    assert len(action_deps) == 1
    assert action_deps[0].requirement.identifier == "city.market"
