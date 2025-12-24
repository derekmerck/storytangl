"""Integration tests for resolving role dependencies during planning."""
from __future__ import annotations

import pytest

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.vm import ResolutionPhase
from tangl.vm.frame import Frame
from tangl.vm.provision import Dependency


@pytest.fixture(autouse=True)
def clear_world():
    World.clear_instances()
    yield
    World.clear_instances()


def _build_world(script_data: dict) -> World:
    script = StoryScript.model_validate(script_data)
    manager = ScriptManager.from_master_script(master_script=script)
    return World(
        label="role_resolution",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def test_planning_phase_resolves_role_dependencies():
    """Planning should provision providers for role dependencies in lazy mode."""

    world = _build_world(
        {
            "label": "planning_test",
            "metadata": {"title": "Planning", "author": "Tests"},
            "templates": {
                "merchant": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "merchant",
                    "name": "Merchant",
                }
            },
            "scenes": {
                "market": {
                    "label": "market",
                    "blocks": {
                        "stall": {
                            "label": "stall",
                            "content": "Market stall",
                            "roles": [
                                {
                                    "label": "vendor",
                                    "actor_template_ref": "merchant",
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="lazy")
    stall = graph.find_node(label="stall")

    dependencies = list(graph.find_edges(source=stall, is_instance=Dependency))
    vendor_dep = [edge for edge in dependencies if edge.label == "vendor"][0]

    assert not vendor_dep.requirement.satisfied
    assert vendor_dep.requirement.provider is None

    frame = Frame(graph=graph, cursor_id=stall.uid)
    frame.run_phase(ResolutionPhase.PLANNING)
    frame.run_phase(ResolutionPhase.UPDATE)

    assert vendor_dep.requirement.satisfied
    assert vendor_dep.requirement.provider is not None
    assert vendor_dep.requirement.provider.name == "Merchant"


def test_soft_requirement_allows_progress_when_unresolved():
    """Soft requirements should be considered satisfied even if no provider exists."""

    world = _build_world(
        {
            "label": "soft_req",
            "metadata": {"title": "Soft Req", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "optional",
                                    "actor_template_ref": "nonexistent_template",
                                    "hard": False,
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="lazy")
    block = graph.find_node(label="block1")

    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    optional_dep = dependencies[0]

    frame = Frame(graph=graph, cursor_id=block.uid)
    frame.run_phase(ResolutionPhase.PLANNING)
    frame.run_phase(ResolutionPhase.UPDATE)

    assert optional_dep.requirement.satisfied
    assert optional_dep.requirement.provider is None


def test_hard_requirement_remains_unsatisfied_when_missing():
    """Hard requirements should stay unresolved if no template exists."""

    world = _build_world(
        {
            "label": "hard_req",
            "metadata": {"title": "Hard Req", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "block1": {
                            "label": "block1",
                            "content": "Block",
                            "roles": [
                                {
                                    "label": "impossible",
                                    "actor_template_ref": "missing_template",
                                    "hard": True,
                                }
                            ],
                        }
                    },
                }
            },
        }
    )

    graph = world.create_story("test", mode="lazy")
    block = graph.find_node(label="block1")

    dependencies = list(graph.find_edges(source=block, is_instance=Dependency))
    hard_dep = dependencies[0]

    frame = Frame(graph=graph, cursor_id=block.uid)
    frame.run_phase(ResolutionPhase.PLANNING)
    frame.run_phase(ResolutionPhase.UPDATE)

    assert not hard_dep.requirement.satisfied
    assert hard_dep.requirement.provider is None
