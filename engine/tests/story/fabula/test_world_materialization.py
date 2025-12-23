"""Tests for ``World._materialize_from_template`` unified materialization."""

from __future__ import annotations

import pytest
from tangl.core.graph import Node
from tangl.ir.story_ir import ActorScript, BlockScript, StoryScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.story.story_graph import StoryGraph


def _empty_story_script() -> StoryScript:
    return StoryScript.model_validate(
        {
            "label": "empty", 
            "metadata": {"title": "Empty", "author": "Tests"},
            "scenes": {},
        }
    )


@pytest.fixture(autouse=True)
def clear_world_singleton():
    """Reset World singleton between tests."""

    World.clear_instances()
    yield
    World.clear_instances()


@pytest.fixture
def mock_world():
    """Create a minimal world for testing."""

    World.clear_instances()

    domain_manager = DomainManager()
    asset_manager = AssetManager()
    script_manager = ScriptManager(master_script=_empty_story_script())

    world = World(
        label="test_world",
        script_manager=script_manager,
        domain_manager=domain_manager,
        asset_manager=asset_manager,
        resource_manager=None,
        metadata={},
    )
    return world


def test_materialize_actor_from_template(mock_world):
    """Actor templates should materialize through domain pipeline."""

    template = ActorScript(
        label="guard",
        obj_cls="tangl.story.concepts.actor.actor.Actor",
        name="Castle Guard",
        hp=100,
    )

    graph = StoryGraph(label="test", world=mock_world)

    actor = mock_world._materialize_from_template(template, graph)

    assert actor.label == "guard"
    assert actor.name == "Castle Guard"
    assert actor in graph


def test_materialize_respects_custom_obj_cls():
    """Custom obj_cls should be resolved via domain_manager."""

    World.clear_instances()

    class CustomWarrior(Node):
        model_config = {"extra": "allow"}

        def __init__(self, label, power_level=0, graph=None, **kwargs):
            power = kwargs.pop("power_level", power_level)
            super().__init__(label=label, graph=graph, **kwargs)
            self.power_level = power

        @classmethod
        def structure(cls, data):
            return cls(**data)

    domain_manager = DomainManager()
    domain_manager.register_class("CustomWarrior", CustomWarrior)

    world = World(
        label="custom_world",
        script_manager=ScriptManager(master_script=_empty_story_script()),
        domain_manager=domain_manager,
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    template = ActorScript(
        label="hero",
        obj_cls="CustomWarrior",
        power_level=9000,
    )

    graph = StoryGraph(label="test", world=world)
    warrior = world._materialize_from_template(template, graph)

    assert isinstance(warrior, CustomWarrior)
    assert warrior.power_level == 9000


def test_materialize_adds_to_parent_container(mock_world):
    """Nodes should be added to parent container if provided."""

    graph = StoryGraph(label="test", world=mock_world)
    scene = graph.add_subgraph(label="village")

    template = ActorScript(
        label="guard",
        obj_cls="tangl.core.graph.Node",
    )

    actor = mock_world._materialize_from_template(
        template, graph, parent_container=scene
    )

    assert actor in scene.members
    assert actor.parent == scene


def test_lazy_mode_does_not_pre_provision_scenes(mock_world):
    """Lazy mode should only materialize the seed block and its scene."""

    story_data = {
        "label": "multi_scene",
        "metadata": {"title": "Multi", "author": "Tests", "start_at": "scene1.start"},
        "scenes": {
            "scene1": {
                "label": "scene1",
                "blocks": {
                    "start": {"label": "start", "text": "Scene 1"}
                },
            },
            "scene2": {
                "label": "scene2",
                "blocks": {
                    "start": {"label": "start", "text": "Scene 2"}
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

    scene1 = graph.get("scene1")
    scene2 = graph.get("scene2")

    assert scene1 is not None, "Seed scene should materialize for the start block"
    assert scene2 is None, "Scene2 should not be pre-provisioned in lazy mode"

    # Only the seed block should exist initially
    start_block = graph.get("start")
    assert start_block is not None
    assert len(list(graph.subgraphs)) == 1
    from tangl.story.episode.block import Block

    blocks = [node for node in graph.nodes if isinstance(node, Block)]
    assert len(blocks) == 1
    assert start_block.parent == scene1


def test_materialize_block_creates_action_edges(mock_world):
    """Blocks with actions should have edges with requirements."""

    from tangl.story.episode.action import Action
    from tangl.story.episode.block import Block

    template = BlockScript(
        label="start",
        # scope=ScopeSelector(parent_label="scene1"),
        obj_cls=Block,
        text="Beginning",
        actions=[{"text": "Continue", "successor": "next"}],
    )

    graph = StoryGraph(label="test", world=mock_world)
    scene = graph.add_subgraph(label="scene1")

    block = mock_world._materialize_from_template(template, graph, scene)

    assert block.label == "start"

    from tangl.vm.provision.open_edge import Dependency

    actions = list(graph.find_edges(is_instance=Action))
    assert len(actions) == 1

    action = actions[0]
    assert action.content == "Continue"
    assert action.destination is None

    dependencies = list(graph.find_edges(is_instance=Dependency, source=action))
    assert len(dependencies) == 1

    requirement = dependencies[0].requirement
    assert requirement.identifier == "scene1.next"
    assert requirement.policy.name == "CREATE"


def test_materialize_block_without_actions(mock_world):
    """Blocks without actions should work fine."""

    from tangl.story.episode.block import Block

    template = BlockScript(label="terminal", obj_cls=Block, text="The end")

    graph = StoryGraph(label="test", world=mock_world)
    block = mock_world._materialize_from_template(template, graph)

    assert block.label == "terminal"
    assert len(list(block.edges_out())) == 0
