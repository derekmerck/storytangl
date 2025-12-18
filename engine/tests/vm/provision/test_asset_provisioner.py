from __future__ import annotations

import pytest
from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.story_graph import StoryGraph
from tangl.vm.provision import (
    AssetProvisioner,
    ProvisionCost,
    ProvisioningContext,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


@pytest.fixture(autouse=True)
def clear_world_instances():
    World.clear_instances()
    yield
    World.clear_instances()


@pytest.fixture
def asset_manager() -> AssetManager:
    manager = AssetManager()
    manager.register(
        asset_ref="Excalibur",
        template={
            "obj_cls": "tangl.core.graph.Node",
            "label": "Excalibur",
            "name": "The Legendary Sword",
        },
    )
    manager.register(
        asset_ref="standard_deck",
        template={
            "obj_cls": "tangl.core.graph.Node",
            "label": "deck",
            "name": "Deck of Cards",
        },
    )
    return manager


def _world_with_assets(asset_manager: AssetManager) -> World:
    script = StoryScript.model_validate(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {},
        }
    )
    return World(
        label="test",
        script_manager=ScriptManager(master_script=script),
        domain_manager=DomainManager(),
        asset_manager=asset_manager,
        resource_manager=None,
        metadata={},
    )


def test_asset_provisioner_requires_explicit_asset_ref(asset_manager: AssetManager) -> None:
    world = _world_with_assets(asset_manager)
    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        template_ref="guard_template",
        criteria={"archetype": "guard"},
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_asset_provisioner_offers_when_asset_ref_present(asset_manager: AssetManager) -> None:
    world = _world_with_assets(asset_manager)
    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        asset_ref="Excalibur",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    assert offers[0].cost == ProvisionCost.HEAVY_INDIRECT


def test_asset_provisioner_skips_if_asset_not_registered(asset_manager: AssetManager) -> None:
    world = _world_with_assets(asset_manager)
    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        asset_ref="NonexistentAsset",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_asset_offer_creates_token_on_accept(asset_manager: AssetManager) -> None:
    world = _world_with_assets(asset_manager)
    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        asset_ref="Excalibur",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offer = list(provisioner.get_dependency_offers(requirement, ctx=ctx))[0]
    token = offer.accept(ctx=ctx)

    assert token is not None
    assert token.name == "The Legendary Sword"
    assert token in graph


def test_asset_provisioner_supports_template_overlay(asset_manager: AssetManager) -> None:
    world = _world_with_assets(asset_manager)
    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        asset_ref="standard_deck",
        template={"shuffle_state": [2, 5, 1, 3], "owner": "player"},
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offer = list(provisioner.get_dependency_offers(requirement, ctx=ctx))[0]
    token = offer.accept(ctx=ctx)

    assert hasattr(token, "shuffle_state")
    assert token.shuffle_state == [2, 5, 1, 3]
    assert getattr(token, "owner", None) == "player"


def test_templates_preferred_for_story_roles(asset_manager: AssetManager) -> None:
    script_data = {
        "label": "test",
        "metadata": {"title": "Test", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.core.graph.Node",
                "label": "guard",
                "name": "Template Guard",
            }
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    asset_manager.register(
        asset_ref="guard",
        template={
            "obj_cls": "tangl.core.graph.Node",
            "label": "guard",
            "name": "Asset Guard",
        },
    )

    world = World(
        label="test",
        script_manager=ScriptManager(master_script=script),
        domain_manager=DomainManager(),
        asset_manager=asset_manager,
        resource_manager=None,
        metadata={},
    )

    graph = StoryGraph(label="test", world=world)

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    asset_prov = AssetProvisioner(layer="asset")
    template_prov = TemplateProvisioner(layer="author")
    ctx = ProvisioningContext(graph=graph, step=0)

    asset_offers = list(asset_prov.get_dependency_offers(requirement, ctx=ctx))
    template_offers = list(template_prov.get_dependency_offers(requirement, ctx=ctx))

    assert asset_offers == []
    assert len(template_offers) == 1

    guard = template_offers[0].accept(ctx=ctx)
    assert guard.label == "guard"

