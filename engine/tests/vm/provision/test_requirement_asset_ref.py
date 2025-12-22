from __future__ import annotations

import pytest

from tangl.core.graph import Graph
from tangl.vm.provision import ProvisioningPolicy, Requirement


def test_requirement_with_token_ref():
    graph = Graph(label="test")

    req = Requirement(graph=graph, token_ref="Excalibur", policy=ProvisioningPolicy.CREATE_TOKEN)

    assert req.token_ref == "Excalibur"
    assert req.template_ref is None
    assert req.identifier is None


def test_requirement_token_ref_optional_defaults():
    graph = Graph(label="test")

    req = Requirement(graph=graph, template_ref="guard_template", policy=ProvisioningPolicy.CREATE_TEMPLATE)

    assert req.token_ref is None
    assert req.template_ref == "guard_template"


def test_requirement_accepts_token_ref_for_any_validation():
    graph = Graph(label="test")

    req = Requirement(graph=graph, token_ref="singleton_token")

    assert req.policy is ProvisioningPolicy.ANY
    assert req.token_ref == "singleton_token"


def test_requirement_with_token_ref_and_template_overlay():
    graph = Graph(label="test")

    req = Requirement(
        graph=graph,
        token_ref="standard_deck",
        template_ref="card_deck_template",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    assert req.token_ref == "standard_deck"
    assert req.template_ref == "card_deck_template"


def test_requirement_serialization_includes_token_ref():
    graph = Graph(label="test")

    req = Requirement(graph=graph, token_ref="legendary_sword", criteria={"damage": 100})

    data = req.model_dump()

    assert data["token_ref"] == "legendary_sword"
    assert data["criteria"]["damage"] == 100


def test_requirement_parses_token_ref_into_type_and_label():
    graph = Graph(label="test")

    req = Requirement(graph=graph, token_ref="Weapon.sword", policy=ProvisioningPolicy.CREATE_TOKEN)

    assert req.token_type == "Weapon"
    assert req.token_label == "sword"


def test_requirement_create_token_requires_reference_or_type_label():
    graph = Graph(label="test")

    with pytest.raises(ValueError, match="CREATE_TOKEN requires"):
        Requirement(graph=graph, policy=ProvisioningPolicy.CREATE_TOKEN)
