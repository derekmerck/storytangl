from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core.graph import Graph
from tangl.core.graph.node import Node
from tangl.vm.context import Context
from tangl.vm.provision.offers import AffordanceOffer, DependencyOffer, ProvisionCost
from tangl.vm.provision.open_edge import Affordance, Dependency
from tangl.vm.provision.requirement import ProvisioningPolicy, Requirement


@pytest.fixture
def dependency_offer_setup():
    graph = Graph()
    source = graph.add_node(label="source")
    provider = graph.add_node(label="provider")

    requirement = Requirement(
        graph=graph,
        identifier=provider.uid,
        policy=ProvisioningPolicy.ANY,
    )
    dependency = Dependency(graph=graph, source=source, requirement=requirement)

    ctx = Context(graph=graph, cursor_id=source.uid)

    calls: list[str] = []

    def acceptor(
        *,
        ctx: Context,
        requirement: Requirement,
        dependency: Dependency | None = None,
        **kwargs,
    ) -> Node:
        calls.append("accepted")
        assert ctx is ctx_ref
        assert requirement is requirement_ref
        assert dependency is dependency_ref
        return provider

    ctx_ref = ctx
    requirement_ref = requirement
    dependency_ref = dependency

    offer = DependencyOffer(
        requirement_id=requirement.uid,
        dependency_id=dependency.uid,
        cost=ProvisionCost(weight=2.0, layer_penalty=0.25),
        layer_id=uuid4(),
        source_provisioner_id=uuid4(),
        proximity=2,
        acceptor=acceptor,
    )

    return {
        "offer": offer,
        "ctx": ctx,
        "calls": calls,
        "provider": provider,
        "requirement": requirement,
        "dependency": dependency,
    }


@pytest.fixture
def affordance_offer_setup():
    graph = Graph()
    destination = graph.add_node(label="destination")
    override_destination = graph.add_node(label="override")

    requirement = Requirement(
        graph=graph,
        criteria={"label": "source"},
        policy=ProvisioningPolicy.ANY,
    )
    affordance = Affordance(graph=graph, destination=destination, requirement=requirement)

    ctx = Context(graph=graph, cursor_id=destination.uid)

    calls: list[dict[str, object]] = []

    def acceptor(
        *,
        ctx: Context,
        affordance: Affordance,
        requirement: Requirement,
        destination: Node | None = None,
        **kwargs,
    ) -> Affordance:
        calls.append(
            {
                "ctx": ctx,
                "affordance": affordance,
                "requirement": requirement,
                "destination": destination,
            }
        )
        return affordance

    offer = AffordanceOffer(
        affordance_id=affordance.uid,
        requirement_id=requirement.uid,
        cost=ProvisionCost(weight=1.0, layer_penalty=0.5),
        layer_id=None,
        source_provisioner_id=uuid4(),
        proximity=5,
        acceptor=acceptor,
    )

    return {
        "offer": offer,
        "ctx": ctx,
        "calls": calls,
        "requirement": requirement,
        "affordance": affordance,
        "destination": destination,
        "override": override_destination,
    }


def test_dependency_offer_accept_is_lazy(dependency_offer_setup):
    offer = dependency_offer_setup["offer"]
    ctx = dependency_offer_setup["ctx"]
    calls = dependency_offer_setup["calls"]
    provider = dependency_offer_setup["provider"]
    requirement = dependency_offer_setup["requirement"]
    dependency = dependency_offer_setup["dependency"]

    assert calls == []
    result = offer.accept(ctx=ctx)

    assert result is provider
    assert calls == ["accepted"]

    # Provenance should be unchanged after acceptance.
    assert offer.requirement_id == requirement.uid
    assert offer.dependency_id == dependency.uid
    assert offer.proximity == 2


def test_affordance_offer_accept_allows_destination_override(affordance_offer_setup):
    offer = affordance_offer_setup["offer"]
    ctx = affordance_offer_setup["ctx"]
    calls = affordance_offer_setup["calls"]
    requirement = affordance_offer_setup["requirement"]
    affordance = affordance_offer_setup["affordance"]
    default_destination = affordance_offer_setup["destination"]
    override_destination = affordance_offer_setup["override"]

    assert calls == []

    result_override = offer.accept(ctx=ctx, destination=override_destination)
    assert result_override is affordance

    assert calls[-1]["ctx"] is ctx
    assert calls[-1]["affordance"] is affordance
    assert calls[-1]["requirement"] is requirement
    assert calls[-1]["destination"] is override_destination

    calls.clear()
    result_default = offer.accept(ctx=ctx)
    assert result_default is affordance
    assert calls[-1]["destination"] is default_destination

    # Metadata remains intact across acceptances.
    assert offer.affordance_id == affordance.uid
    assert offer.requirement_id == requirement.uid
    assert offer.source_provisioner_id is not None
    assert offer.proximity == 5
