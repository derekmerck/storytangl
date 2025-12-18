from __future__ import annotations

from tangl.core.graph import Graph
from tangl.vm.provision import ProvisioningPolicy, Requirement


def test_requirement_with_asset_ref():
    graph = Graph(label="test")

    req = Requirement(graph=graph, asset_ref="Excalibur", policy=ProvisioningPolicy.CREATE)

    assert req.asset_ref == "Excalibur"
    assert req.template_ref is None
    assert req.identifier is None


def test_requirement_asset_ref_optional_defaults():
    graph = Graph(label="test")

    req = Requirement(graph=graph, template_ref="guard_template", policy=ProvisioningPolicy.CREATE)

    assert req.asset_ref is None
    assert req.template_ref == "guard_template"


def test_requirement_accepts_asset_ref_for_any_validation():
    graph = Graph(label="test")

    req = Requirement(graph=graph, asset_ref="singleton_token")

    assert req.policy is ProvisioningPolicy.ANY
    assert req.asset_ref == "singleton_token"


def test_requirement_with_asset_ref_and_template_overlay():
    graph = Graph(label="test")

    req = Requirement(
        graph=graph,
        asset_ref="standard_deck",
        template_ref="card_deck_template",
        policy=ProvisioningPolicy.CREATE,
    )

    assert req.asset_ref == "standard_deck"
    assert req.template_ref == "card_deck_template"


def test_requirement_serialization_includes_asset_ref():
    graph = Graph(label="test")

    req = Requirement(graph=graph, asset_ref="legendary_sword", criteria={"damage": 100})

    data = req.model_dump()

    assert data["asset_ref"] == "legendary_sword"
    assert data["criteria"]["damage"] == 100

