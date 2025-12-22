from __future__ import annotations

from types import SimpleNamespace

import pydantic
import pytest

from tangl.core.graph import Graph, Node
from tangl.vm.provision import (
    AssetProvisioner,
    ProvisionCost,
    ProvisioningContext,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


AssetNode = pydantic.create_model(
    "AssetNode",
    __base__=Node,
    name=(str, ""),
    owner=(str | None, None),
    shuffle_state=(list[int], []),
)


class DummyAssetManager:
    def __init__(self) -> None:
        self._assets: dict[str, dict] = {}

    def register(self, asset_ref: str, template: dict) -> None:
        self._assets[asset_ref] = dict(template)

    def has_asset(self, asset_ref: str) -> bool:
        return asset_ref in self._assets

    def create_token(self, asset_ref: str, graph: Graph, **overlay) -> Node:
        payload = dict(self._assets[asset_ref])
        payload.update(overlay)
        payload.setdefault("obj_cls", AssetNode)
        payload.setdefault("graph", graph)
        return Node.structure(payload)


@pytest.fixture
def asset_manager() -> DummyAssetManager:
    manager = DummyAssetManager()
    manager.register(
        asset_ref="Excalibur",
        template={
            "obj_cls": AssetNode,
            "label": "Excalibur",
            "name": "The Legendary Sword",
        },
    )
    manager.register(
        asset_ref="standard_deck",
        template={
            "obj_cls": AssetNode,
            "label": "deck",
            "name": "Deck of Cards",
        },
    )
    return manager


def _graph_with_assets(asset_manager: DummyAssetManager) -> Graph:
    graph = Graph(label="test")
    world = SimpleNamespace(asset_manager=asset_manager, domain_manager=None)
    object.__setattr__(graph, "world", world)
    return graph


def test_asset_provisioner_requires_explicit_asset_ref(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

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


def test_asset_provisioner_offers_when_asset_ref_present(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

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


def test_asset_provisioner_skips_if_asset_not_registered(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        asset_ref="NonexistentAsset",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = AssetProvisioner(layer="asset")
    ctx = ProvisioningContext(graph=graph, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_asset_offer_creates_token_on_accept(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

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


def test_asset_provisioner_supports_template_overlay(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

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


def test_templates_preferred_for_story_roles(asset_manager: DummyAssetManager) -> None:
    graph = _graph_with_assets(asset_manager)

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
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
