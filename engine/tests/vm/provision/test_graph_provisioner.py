from tangl.core.graph import Graph
from tangl.vm.context import Context
from tangl.vm.provision.graph_provisioner import GraphProvisioner
from tangl.vm.provision.requirement import ProvisioningPolicy, Requirement


def test_graph_provisioner_only_emits_offers_for_matching_nodes() -> None:
    graph = Graph()
    _matching = graph.add_node(label="target")
    graph.add_node(label="other")

    requirement = Requirement(
        graph=graph,
        criteria={"label": "target"},
        policy=ProvisioningPolicy.EXISTING,
    )
    graph.add(requirement)

    provisioner = GraphProvisioner(graph=graph)

    offers = list(provisioner.iter_dependency_offers(requirement=requirement))

    assert len(offers) == 1

    offer = offers[0]
    assert offer.requirement_id == requirement.uid
    assert offer.source_provisioner_id == provisioner.uid
    assert offer.operation is ProvisioningPolicy.EXISTING
    assert offer.proximity == 0
    assert offer.cost.weight == provisioner.cost_weight
    assert offer.cost.proximity == 0
    assert offer.cost.layer_penalty == 0.0

    unmatched_requirement = Requirement(
        graph=graph,
        criteria={"label": "missing"},
        policy=ProvisioningPolicy.EXISTING,
    )
    graph.add(unmatched_requirement)

    assert list(provisioner.iter_dependency_offers(requirement=unmatched_requirement)) == []


def test_graph_provisioner_offer_accept_returns_existing_node_without_side_effects() -> None:
    graph = Graph()
    provider = graph.add_node(label="provider")

    requirement = Requirement(
        graph=graph,
        identifier=provider.uid,
        policy=ProvisioningPolicy.EXISTING,
    )
    graph.add(requirement)

    provisioner = GraphProvisioner(graph=graph)
    offers = list(provisioner.iter_dependency_offers(requirement=requirement))

    assert len(offers) == 1

    offer = offers[0]
    ctx = Context(graph=graph, cursor_id=provider.uid)

    before_nodes = set(graph.data.keys())
    assert requirement.provider is None

    resolved = offer.accept(ctx=ctx)

    assert resolved is provider
    assert requirement.provider is None
    assert set(graph.data.keys()) == before_nodes

