from __future__ import annotations

import pytest

from tangl.core.graph import Graph
from tangl.vm.context import Context
from tangl.vm.provision.graph_provisioner import GraphProvisioner
from tangl.vm.provision.open_edge import Dependency
from tangl.vm.provision.requirement import ProvisioningPolicy, Requirement


@pytest.fixture
def graph_setup():
    graph = Graph()
    source = graph.add_node(label="source")
    matching = graph.add_node(label="target")
    _ = graph.add_node(label="bystander")

    requirement = Requirement(
        graph=graph,
        criteria={"label": "target"},
        policy=ProvisioningPolicy.EXISTING,
    )
    dependency = Dependency(graph=graph, source=source, requirement=requirement)

    return {
        "graph": graph,
        "source": source,
        "matching": matching,
        "requirement": requirement,
        "dependency": dependency,
    }


def test_graph_provisioner_only_emits_matching_offers(graph_setup):
    provisioner = GraphProvisioner()
    requirement = graph_setup["requirement"]
    dependency = graph_setup["dependency"]

    offers = list(
        provisioner.iter_dependency_offers(
            requirement,
            dependency=dependency,
        )
    )

    assert len(offers) == 1
    offer = offers[0]

    assert offer.operation is ProvisioningPolicy.EXISTING
    assert offer.layer_id == graph_setup["graph"].uid
    assert offer.cost.proximity == 0
    assert offer.proximity == 0


def test_graph_provisioner_accept_returns_existing_node(graph_setup):
    provisioner = GraphProvisioner()
    graph = graph_setup["graph"]
    source = graph_setup["source"]
    requirement = graph_setup["requirement"]
    dependency = graph_setup["dependency"]
    matching = graph_setup["matching"]

    offers = list(
        provisioner.iter_dependency_offers(
            requirement,
            dependency=dependency,
        )
    )

    ctx = Context(graph=graph, cursor_id=source.uid)

    assert requirement.provider is None

    offer = offers[0]
    provider = offer.accept(ctx=ctx)

    assert provider is matching
    assert requirement.provider is None

    # Graph should remain unchanged during offer generation and acceptance.
    nodes = list(graph.find_nodes())
    labels = {node.label for node in nodes}
    assert labels == {"source", "target", "bystander"}
