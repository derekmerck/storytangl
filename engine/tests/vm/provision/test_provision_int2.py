"""Integration tests documenting planning dispatch expectations."""

from types import SimpleNamespace

import pytest

from tangl.core import Graph
from tangl.vm.provision import (
    CloningProvisioner,
    GraphProvisioner,
    Requirement,
    ProvisioningPolicy,
)


def test_proximity_calculation_prefers_local_provisioners():
    graph = Graph()
    scene = graph.add_node(label="scene")
    block = graph.add_node(label="block")

    local = GraphProvisioner(node_registry=graph, layer="local", scope_node_id=scene.uid)
    global_prov = GraphProvisioner(node_registry=graph, layer="global", scope_node_id=None)

    # TODO: planning dispatch will calculate proximity between block and provisioners
    # local_proximity = calculate_provisioner_proximity(local, block)
    # global_proximity = calculate_provisioner_proximity(global_prov, block)
    # assert local_proximity < global_proximity


def test_deduplication_keeps_cheapest_offer():
    graph = Graph()
    door = graph.add_node(label="door")
    requirement = Requirement(
        graph=graph,
        identifier="door",
        policy=ProvisioningPolicy.EXISTING,
    )

    local = GraphProvisioner(node_registry=graph, layer="local")
    distant = GraphProvisioner(node_registry=graph, layer="global")
    ctx = SimpleNamespace(graph=graph)

    local_offer = next(iter(local.get_dependency_offers(requirement, ctx=ctx)))
    distant_offer = next(iter(distant.get_dependency_offers(requirement, ctx=ctx)))

    assert local_offer.provider_id == door.uid
    assert distant_offer.provider_id == door.uid

    # TODO: planning dispatch will deduplicate offers for the same provider
    # offers = [local_offer, distant_offer]
    # deduped = deduplicate_offers(offers)
    # assert len(deduped) == 1


def test_scoped_binding_inheritance():
    graph = Graph()
    scene = graph.add_node(label="scene")
    block = graph.add_node(label="block")
    villain = graph.add_node(label="villain")

    requirement = Requirement(
        graph=graph,
        identifier="villain",
        policy=ProvisioningPolicy.EXISTING,
    )

    requirement.provider = villain
    requirement.satisfied_at_scope_id = scene.uid

    # TODO: planning dispatch will detect that block inherits villain binding
    # inherited = should_provision_requirement(requirement, block)
    # assert not inherited


def test_clone_offer_uses_reference_node():
    graph = Graph()
    template_source = graph.add_node(label="alice")

    requirement = Requirement(
        graph=graph,
        policy=ProvisioningPolicy.CLONE,
        reference_id=template_source.uid,
        template={"label": "alice_clone"},
    )

    provisioner = CloningProvisioner(node_registry=graph)
    ctx = SimpleNamespace(graph=graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    # TODO: planning dispatch should evaluate cost/proximity before accepting clones
    # selected = select_best_offer(offers)
    # assert selected.provider_id is None
