from __future__ import annotations

from tangl.core import Graph, Node
from tangl.vm.provision import (
    CompanionProvisioner,
    Dependency,
    GraphProvisioner,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
    provision_node,
    ProvisioningContext,
)


def _ctx(graph: Graph, step: int = 0) -> ProvisioningContext:
    return ProvisioningContext(graph=graph, step=step)


def test_provision_with_existing_resource():
    graph = Graph()
    key = graph.add_node(label="gold_key")
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="gold_key",
        policy=ProvisioningPolicy.EXISTING,
    )
    dependency = Dependency(graph=graph, source=scene, requirement=requirement, label="needs_key")

    provisioners = [GraphProvisioner(node_registry=graph)]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert result.is_viable
    assert dependency.destination is key
    offers = result.dependency_offers[requirement.uid]
    assert len(offers) == 1
    assert offers[0].provider_id == key.uid


def test_provision_creates_when_missing():
    graph = Graph()
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        template={"obj_cls": Node, "label": "generated_key"},
        policy=ProvisioningPolicy.CREATE,
    )
    dependency = Dependency(graph=graph, source=scene, requirement=requirement, label="needs_generated")

    provisioners = [TemplateProvisioner(layer="author")]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert dependency.destination is not None
    assert dependency.destination.label == "generated_key"
    assert dependency.destination in graph
    assert result.is_viable


def test_provision_marks_hard_requirement_failure():
    graph = Graph()
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="missing",
        policy=ProvisioningPolicy.EXISTING,
    )
    Dependency(graph=graph, source=scene, requirement=requirement, label="needs_missing")

    provisioners = [GraphProvisioner(node_registry=graph)]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert not result.is_viable
    assert requirement.uid in result.dependency_offers
    assert result.dependency_offers[requirement.uid] == []
    failure = next(receipt for receipt in result.builds if receipt.caller_id == requirement.uid)
    assert not failure.accepted
    assert failure.reason == "No offers available"


def test_provision_satisfies_soft_requirements_opportunistically():
    graph = Graph()
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="optional",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=False,
    )
    Dependency(graph=graph, source=scene, requirement=requirement, label="needs_optional")

    provisioners = [GraphProvisioner(node_registry=graph)]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert result.is_viable
    assert requirement.uid in result.dependency_offers
    assert result.dependency_offers[requirement.uid] == []
    assert all(receipt.requirement_id != requirement.uid for receipt in result.builds)


def test_provision_deduplicates_existing_offers():
    graph = Graph()
    provider = graph.add_node(label="oak_door")
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="oak_door",
        policy=ProvisioningPolicy.EXISTING,
    )
    Dependency(graph=graph, source=scene, requirement=requirement, label="needs_door")

    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        GraphProvisioner(node_registry=graph, layer="global"),
    ]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    offers = result.dependency_offers[requirement.uid]
    assert len(offers) == 1
    assert offers[0].provider_id == provider.uid
    build = next(receipt for receipt in result.builds if receipt.caller_id == requirement.uid)
    assert build.accepted


def test_provision_accepts_best_offer_by_cost():
    graph = Graph()
    existing = graph.add_node(label="door")
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="door",
        template={"obj_cls": Node, "label": "door"},
        policy=ProvisioningPolicy.ANY,
    )
    dependency = Dependency(graph=graph, source=scene, requirement=requirement, label="needs_door")

    provisioners = [
        TemplateProvisioner(layer="author"),
        GraphProvisioner(node_registry=graph, layer="local"),
    ]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert dependency.destination is existing
    build = next(receipt for receipt in result.builds if receipt.caller_id == requirement.uid)
    assert build.operation is ProvisioningPolicy.EXISTING


def test_provision_handles_affordances():
    graph = Graph()
    ally = graph.add_node(label="ally", tags={"happy"})
    scene = graph.add_node(label="stage", tags={"musical"})

    dependency = Requirement(
        graph=graph,
        identifier="ally",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=False,
    )
    dep_edge = Dependency(graph=graph, source=scene, requirement=dependency, label="needs_ally")

    provisioners = [
        CompanionProvisioner(companion_node=ally, layer="local"),
        GraphProvisioner(node_registry=graph, layer="local"),
    ]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    assert any(offer.label == "talk" for offer in result.affordance_offers)
    assert dep_edge.destination is ally
    assert result.is_viable


def test_provision_result_tracks_all_offers():
    graph = Graph()
    existing = graph.add_node(label="door")
    scene = graph.add_node(label="scene")

    requirement = Requirement(
        graph=graph,
        identifier="door",
        template={"obj_cls": Node, "label": "door"},
        policy=ProvisioningPolicy.ANY,
    )
    Dependency(graph=graph, source=scene, requirement=requirement, label="needs_door")

    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(layer="author"),
    ]
    result = provision_node(scene, provisioners, ctx=_ctx(graph))

    offers = result.dependency_offers[requirement.uid]
    assert {offer.operation for offer in offers} == {
        ProvisioningPolicy.EXISTING,
        ProvisioningPolicy.CREATE,
    }
    assert any(receipt.provider_id == existing.uid for receipt in result.builds)
