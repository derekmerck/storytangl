"""Integration tests for lazy block provisioning via template system."""

import pytest

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.provision import ProvisioningPolicy


@pytest.fixture(autouse=True)
def clear_world_singleton():
    """Reset World singleton between tests."""
    World.clear_instances()
    yield
    World.clear_instances()


def test_lazy_block_provisioning_from_template_registry():
    """
    Lazy story creates seed block with action edges (open Requirements).
    Planning resolves Requirements, provisions successor blocks on-demand.
    Actions complete when destinations bind.

    This is the definition-of-done test for issue #106.
    """

    story_data = {
        "label": "test_story",
        "metadata": {
            "title": "Test Story",
            "author": "Tests",
            "start_at": "scene1.start",
        },
        "scenes": {
            "scene1": {
                "label": "scene1",
                "blocks": {
                    "start": {
                        "label": "start",
                        "block_cls": "tangl.story.episode.block.Block",
                        "content": "You stand at the beginning.",
                        "actions": [
                            {
                                "text": "Continue forward",
                                "successor": "next",
                            }
                        ],
                    },
                    "next": {
                        "label": "next",
                        "block_cls": "tangl.story.episode.block.Block",
                        "content": "You have advanced to the next location.",
                    },
                },
            }
        },
    }

    script = StoryScript.model_validate(story_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="test_story",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=story_data["metadata"],
    )

    start_template = world.template_registry.find_one(identifier="scene1.start")
    next_template = world.template_registry.find_one(identifier="scene1.next")

    assert start_template is not None, "Start block template not registered"
    assert next_template is not None, "Next block template not registered"
    assert start_template.content == "You stand at the beginning."
    assert next_template.content == "You have advanced to the next location."

    graph = world.create_story("test_run", mode="lazy")

    scene1 = graph.find_subgraph(label="scene1")
    assert scene1 is not None, "Scene should be pre-provisioned"

    start_block = graph.find_node(label="start")
    assert start_block is not None, "Seed block not created"
    assert start_block.content == "You stand at the beginning."
    assert start_block.parent == scene1, "Block should be in scene"

    next_block = graph.find_node(label="next")
    assert next_block is None, "Next block should not be materialized yet (lazy mode)"

    from tangl.story.episode.action import Action

    actions = list(start_block.edges_out(is_instance=Action))
    assert len(actions) == 1, "Action edge not created"

    action = actions[0]
    assert action.content == "Continue forward"
    assert action.destination is None, "Action destination should be open (not resolved yet)"

    from tangl.vm.provision.open_edge import Dependency

    dependencies = list(graph.find_edges(source=action, is_instance=Dependency))
    assert len(dependencies) == 1, "Action should have destination requirement"

    req = dependencies[0].requirement
    assert req.identifier == "scene1.next", "Requirement should reference next block"
    assert req.policy == ProvisioningPolicy.CREATE
    assert not req.satisfied, "Requirement should not be satisfied yet"

    from tangl.vm.provision import TemplateProvisioner
    from types import SimpleNamespace

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(
        graph=graph,
        cursor=None,
        cursor_id=None,
    )

    offers = list(provisioner.get_dependency_offers(req, ctx=ctx))
    assert len(offers) == 1, "Provisioner should offer to create next block"

    provisioned_node = offers[0].accept(ctx=ctx)

    assert provisioned_node is not None
    assert provisioned_node.label == "next"
    assert provisioned_node.content == "You have advanced to the next location."
    assert provisioned_node in graph
    assert provisioned_node.parent == scene1, "Provisioned block should be in scene"

    next_block = graph.find_node(label="next")
    assert next_block == provisioned_node

    req.provider = provisioned_node
    action.destination = provisioned_node

    assert req.satisfied, "Requirement should be satisfied after provisioning"
    assert req.provider == provisioned_node
    assert action.destination == provisioned_node, "Action destination should be bound"

    from tangl.vm.frame import Frame

    frame = Frame(graph=graph, cursor_id=start_block.uid)

    frame.resolve_choice(action)
    assert frame.cursor == provisioned_node, "Should navigate to provisioned block"
    assert frame.cursor.content == "You have advanced to the next location."


def test_lazy_provisioning_with_multiple_successors():
    """Multiple actions should each create requirements for their successors."""

    story_data = {
        "label": "branching",
        "metadata": {
            "title": "Branching Story",
            "author": "Tests",
            "start_at": "hub.center",
        },
        "scenes": {
            "hub": {
                "label": "hub",
                "blocks": {
                    "center": {
                        "label": "center",
                        "block_cls": "tangl.story.episode.block.Block",
                        "content": "You stand at a crossroads.",
                        "actions": [
                            {"text": "Go north", "successor": "north"},
                            {"text": "Go south", "successor": "south"},
                            {"text": "Go east", "successor": "east"},
                        ],
                    },
                    "north": {"label": "north", "block_cls": "tangl.story.episode.block.Block", "content": "Northern path"},
                    "south": {"label": "south", "block_cls": "tangl.story.episode.block.Block", "content": "Southern path"},
                    "east": {"label": "east", "block_cls": "tangl.story.episode.block.Block", "content": "Eastern path"},
                },
            }
        },
    }

    script = StoryScript.model_validate(story_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="branching",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=story_data["metadata"],
    )

    graph = world.create_story("test", mode="lazy")
    center = graph.find_node(label="center")

    from tangl.story.episode.action import Action

    actions = list(center.edges_out(is_instance=Action))
    assert len(actions) == 3

    from tangl.vm.provision.open_edge import Dependency

    for action in actions:
        assert action.destination is None
        reqs = list(graph.find_edges(source=action, is_instance=Dependency))
        assert len(reqs) == 1
        assert not reqs[0].requirement.satisfied

    identifiers = {list(graph.find_edges(source=action, is_instance=Dependency))[0].requirement.identifier for action in actions}
    assert identifiers == {"hub.north", "hub.south", "hub.east"}

    assert graph.find_node(label="north") is None
    assert graph.find_node(label="south") is None
    assert graph.find_node(label="east") is None


def test_lazy_provisioning_across_scene_boundary():
    """Actions can cross scene boundaries in lazy mode."""

    story_data = {
        "label": "multi_scene",
        "metadata": {
            "title": "Cross Scene",
            "author": "Tests",
            "start_at": "forest.entrance",
        },
        "scenes": {
            "forest": {
                "label": "forest",
                "blocks": {
                    "entrance": {
                        "label": "entrance",
                        "block_cls": "tangl.story.episode.block.Block",
                        "content": "You stand at the forest edge.",
                        "actions": [
                            {"text": "Enter cave", "successor": "cave.mouth"}
                        ],
                    }
                },
            },
            "cave": {
                "label": "cave",
                "blocks": {
                    "mouth": {
                        "label": "mouth",
                        "block_cls": "tangl.story.episode.block.Block",
                        "content": "You enter the dark cave.",
                    }
                },
            },
        },
    }

    script = StoryScript.model_validate(story_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="multi_scene",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=story_data["metadata"],
    )

    graph = world.create_story("test", mode="lazy")

    forest_scene = graph.find_subgraph(label="forest")
    cave_scene = graph.find_subgraph(label="cave")
    assert forest_scene is not None
    assert cave_scene is not None

    entrance = graph.find_node(label="entrance")
    assert entrance is not None
    assert entrance.parent == forest_scene

    cave_mouth = graph.find_node(label="mouth")
    assert cave_mouth is None

    from tangl.story.episode.action import Action

    actions = list(entrance.edges_out(is_instance=Action))
    assert len(actions) == 1

    action = actions[0]
    assert action.destination is None

    from tangl.vm.provision.open_edge import Dependency

    dependency = graph.find_edge(source=action, is_instance=Dependency)
    assert dependency is not None
    req = dependency.requirement
    assert req.identifier == "cave.mouth"

    from tangl.vm.provision import TemplateProvisioner
    from types import SimpleNamespace

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(req, ctx=ctx))
    cave_mouth = offers[0].accept(ctx=ctx)

    assert cave_mouth.label == "mouth"
    assert cave_mouth.parent == cave_scene
    assert cave_mouth in cave_scene.members

    req.provider = cave_mouth
    action.destination = cave_mouth

    from tangl.vm.frame import Frame

    frame = Frame(graph=graph, cursor_id=entrance.uid)
    frame.resolve_choice(action)

    assert frame.cursor == cave_mouth
    assert frame.cursor.parent == cave_scene
