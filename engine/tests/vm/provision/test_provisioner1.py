from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tangl.core import Graph, Node
from tangl.core.factory import Template
from tangl.vm.provision import (
    CompanionProvisioner,
    CloningProvisioner,
    GraphProvisioner,
    ProvisionCost,
    Requirement,
    ProvisioningPolicy,
    TemplateProvisioner,
)


def _ctx(graph: Graph, cursor: Node | None = None) -> SimpleNamespace:
    cursor_id = cursor.uid if cursor is not None else None
    return SimpleNamespace(graph=graph, cursor_id=cursor_id)


def test_graph_provisioner_finds_existing_node():
    graph = Graph()
    existing = graph.add_node(label="door", tags={"wooden"})
    requirement = Requirement(
        graph=graph,
        identifier="door",
        policy=ProvisioningPolicy.EXISTING,
    )

    provisioner = GraphProvisioner(node_registry=graph, layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=_ctx(graph, existing)))

    assert len(offers) == 1
    offer = offers[0]
    assert offer.operation is ProvisioningPolicy.EXISTING
    assert offer.base_cost is ProvisionCost.DIRECT
    assert offer.cost == float(ProvisionCost.DIRECT)
    provider = offer.accept(ctx=_ctx(graph, existing))
    assert provider is existing


def test_graph_provisioner_multiple_nodes_no_closure_bug():
    graph = Graph()
    door1 = graph.add_node(label="door1", tags={"wooden"})
    door2 = graph.add_node(label="door2", tags={"wooden"})
    door3 = graph.add_node(label="door3", tags={"wooden"})

    requirement = Requirement(
        graph=graph,
        criteria={"has_tags": {"wooden"}},
        policy=ProvisioningPolicy.EXISTING,
    )

    provisioner = GraphProvisioner(node_registry=graph, layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=_ctx(graph)))

    assert len(offers) == 3
    providers = [offer.accept(ctx=_ctx(graph)) for offer in offers]
    provider_uids = {p.uid for p in providers}

    assert provider_uids == {door1.uid, door2.uid, door3.uid}
    assert {offer.provider_id for offer in offers} == provider_uids


def test_cheapest_offer_wins_existing_over_create():
    graph = Graph()
    existing = graph.add_node(label="door")
    requirement = Requirement(
        graph=graph,
        identifier="door",
        template=Template[Node](label="door", obj_cls=Node),
        policy=ProvisioningPolicy.ANY,
    )

    graph_prov = GraphProvisioner(node_registry=graph, layer="local")
    template_prov = TemplateProvisioner(layer="author")

    offers = []
    offers.extend(graph_prov.get_dependency_offers(requirement, ctx=_ctx(graph)))
    offers.extend(template_prov.get_dependency_offers(requirement, ctx=_ctx(graph)))

    offers.sort(key=lambda offer: offer.cost)
    best = offers[0]
    assert best.operation is ProvisioningPolicy.EXISTING
    assert best.accept(ctx=_ctx(graph)) is existing


def test_affordance_offer_filters_by_tags():
    graph = Graph()
    companion = graph.add_node(label="ally", tags={"happy"})
    musical_scene = graph.add_node(label="stage", tags={"musical"})
    quiet_scene = graph.add_node(label="ruins", tags={"silent"})

    provisioner = CompanionProvisioner(companion_node=companion, layer="local")
    offers = list(provisioner.get_affordance_offers(musical_scene, ctx=_ctx(graph)))

    assert {offer.label for offer in offers} == {"talk", "sing"}

    sing_offer = next(offer for offer in offers if offer.label == "sing")
    assert sing_offer.available_for(musical_scene)
    assert not sing_offer.available_for(quiet_scene)

    edge = sing_offer.accept(ctx=_ctx(graph), destination=musical_scene)
    assert edge.destination is musical_scene
    assert edge.source is companion


def test_cloning_provisioner_missing_reference_returns_no_offers():
    graph = Graph()
    provisioner = CloningProvisioner(node_registry=graph)
    requirement = Requirement(
        graph=graph,
        policy=ProvisioningPolicy.CLONE,
        reference_id=uuid4(),
        template=Template[Node](label="clone"),
    )

    offers = list(provisioner.get_dependency_offers(requirement, ctx=_ctx(graph)))
    assert offers == []


def test_cloning_provisioner_clones_reference_node():
    graph = Graph()
    source = graph.add_node(label="prototype", tags={"alpha"})
    provisioner = CloningProvisioner(node_registry=graph)
    requirement = Requirement(
        graph=graph,
        policy=ProvisioningPolicy.CLONE,
        reference_id=source.uid,
        template=Template[Node](label="prototype_clone", tags={"alpha", "beta"}),
    )

    offers = list(provisioner.get_dependency_offers(requirement, ctx=_ctx(graph)))

    assert len(offers) == 1
    clone = offers[0].accept(ctx=_ctx(graph))

    assert clone is not source
    assert clone.label == "prototype_clone"
    assert clone.tags == {"alpha", "beta"}
    assert clone in graph


def test_requirement_clone_requires_reference_id_validation():
    graph = Graph()

    with pytest.raises(ValidationError, match="reference_id"):
        Requirement(
            graph=graph,
            policy=ProvisioningPolicy.CLONE,
            template=Template[Node](label="clone"),
        )


def test_requirement_clone_requires_template_validation():
    graph = Graph()
    reference = graph.add_node(label="template_ref")

    with pytest.raises(ValidationError, match="template"):
        Requirement(
            graph=graph,
            policy=ProvisioningPolicy.CLONE,
            reference_id=reference.uid,
        )
