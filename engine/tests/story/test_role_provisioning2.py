from __future__ import annotations

from tangl.story.concepts.actor.role import Role
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.provision import (
    CloningProvisioner,
    GraphProvisioner,
    ProvisioningContext,
    TemplateProvisioner,
    UpdatingProvisioner,
    provision_node,
)


def test_planner_provisions_role_from_existing_affordance() -> None:
    script = {
        "label": "test",
        "metadata": {
            "title": "Test",
            "author": "Test",
            "start_at": "tavern.start",
        },
        "actors": {
            "bob": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "name": "Bob",
            }
        },
        "scenes": {
            "tavern": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "content": "Tavern.",
                        "roles": {"bartender": {"actor_ref": "bob"}},
                    },
                },
            }
        },
    }

    World.clear_instances()
    script_manager = ScriptManager.from_data(script)
    world = World(
        label="test",
        script_manager=script_manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=script_manager.get_story_metadata(),
    )
    graph = world.create_story("story")

    bob = graph.find_one(label="bob")
    role = graph.find_one(is_instance=Role, label="bartender")
    start = graph.find_one(label="start")

    assert role is not None
    assert bob is not None
    assert role.destination_id is None
    assert role.requirement.identifier == "bob"
    assert start is not None

    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        UpdatingProvisioner(node_registry=graph, layer="local"),
        CloningProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(template_registry=world.template_registry, layer="local"),
    ]
    ctx = ProvisioningContext(graph=graph, step=0)
    result = provision_node(start, provisioners, ctx=ctx)
    plan = result.primary_plan
    assert plan is not None
    receipts = plan.execute(ctx=ctx)
    assert receipts or role.requirement.satisfied

    assert role.requirement.provider_id == bob.uid
    assert role.requirement.provider == bob


def test_planner_provisions_role_from_template() -> None:
    script = {
        "label": "test",
        "metadata": {
            "title": "Test",
            "author": "Test",
            "start_at": "tavern.start",
        },
        "templates": {
            "bartender_npc": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "name": "Generic Bartender",
            }
        },
        "scenes": {
            "tavern": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "content": "Tavern.",
                        "roles": {"bartender": {"actor_template_ref": "bartender_npc"}},
                    },
                },
            }
        },
    }

    World.clear_instances()
    script_manager = ScriptManager.from_data(script)
    world = World(
        label="test",
        script_manager=script_manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=script_manager.get_story_metadata(),
    )
    graph = world.create_story("story")

    role = graph.find_one(is_instance=Role, label="bartender")
    start = graph.find_one(label="start")
    assert role is not None
    assert role.destination_id is None
    assert role.requirement.template_ref == "bartender_npc"
    assert start is not None

    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        UpdatingProvisioner(node_registry=graph, layer="local"),
        CloningProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(template_registry=world.template_registry, layer="local"),
    ]
    ctx = ProvisioningContext(graph=graph, step=0)
    result = provision_node(start, provisioners, ctx=ctx)
    plan = result.primary_plan
    assert plan is not None
    receipts = plan.execute(ctx=ctx)
    assert receipts or role.requirement.satisfied

    assert role.requirement.provider_id is not None
    bartender = role.requirement.provider
    assert bartender is not None
    assert bartender.name == "Generic Bartender"
