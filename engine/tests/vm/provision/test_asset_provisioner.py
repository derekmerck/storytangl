from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import Field

from tangl.core.graph import Graph
from tangl.story.concepts.asset import AssetType
from tangl.story.fabula.asset_manager import AssetManager
from tangl.vm.provision import (
    AssetProvisioner,
    ProvisionCost,
    ProvisioningContext,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


class Weapon(AssetType):
    name: str = ""
    owner: str | None = Field(default=None, json_schema_extra={"instance_var": True})
    shuffle_state: list[int] = Field(
        default_factory=list,
        json_schema_extra={"instance_var": True},
    )


@pytest.fixture(autouse=True)
def _clear_weapon_instances() -> None:
    yield
    Weapon.clear_instances()


@pytest.fixture
def asset_manager() -> AssetManager:
    manager = AssetManager()
    manager.register_discrete_class("weapons", Weapon)
    Weapon(label="Excalibur", name="The Legendary Sword")
    Weapon(label="standard_deck", name="Deck of Cards")
    return manager


def _graph_with_assets(asset_manager: AssetManager) -> Graph:
    graph = Graph(label="test")
    world = SimpleNamespace(asset_manager=asset_manager, domain_manager=None)
    object.__setattr__(graph, "world", world)
    return graph


def test_asset_provisioner_requires_explicit_token_ref(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        template_ref="guard_template",
        criteria={"archetype": "guard"},
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_asset_provisioner_offers_when_token_ref_present(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="Excalibur",
        policy=ProvisioningPolicy.CREATE_TOKEN,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    assert offers[0].cost == ProvisionCost.HEAVY_INDIRECT


def test_asset_provisioner_skips_if_asset_not_registered(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="NonexistentAsset",
        policy=ProvisioningPolicy.CREATE_TOKEN,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_asset_offer_creates_token_on_accept(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="Excalibur",
        policy=ProvisioningPolicy.CREATE_TOKEN,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offer = list(provisioner.get_dependency_offers(requirement, ctx=ctx))[0]
    token = offer.accept(ctx=ctx)

    assert token is not None
    assert token.name == "The Legendary Sword"
    assert token in graph


def test_asset_provisioner_supports_template_overlay(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="standard_deck",
        overlay={"shuffle_state": [2, 5, 1, 3], "owner": "player"},
        policy=ProvisioningPolicy.CREATE_TOKEN,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offer = list(provisioner.get_dependency_offers(requirement, ctx=ctx))[0]
    token = offer.accept(ctx=ctx)

    assert hasattr(token, "shuffle_state")
    assert token.shuffle_state == [2, 5, 1, 3]
    assert getattr(token, "owner", None) == "player"


def test_templates_preferred_for_story_roles(asset_manager: AssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    asset_prov = AssetProvisioner(layer="asset")
    template_prov = TemplateProvisioner(
        factory=None,
        layer="author",
    )
    ctx = ProvisioningContext(graph=graph, step=0)

    asset_offers = list(asset_prov.get_dependency_offers(requirement, ctx=ctx))
    template_offers = list(template_prov.get_dependency_offers(requirement, ctx=ctx))

    assert asset_offers == []
    assert template_offers == []
