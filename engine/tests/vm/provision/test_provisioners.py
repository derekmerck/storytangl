from types import SimpleNamespace

from tangl.core import Graph, Node
from tangl.vm.provision import (
    CompanionProvisioner,
    GraphProvisioner,
    ProvisionCost,
    Requirement,
    ProvisioningPolicy,
    TemplateProvisioner,
)


def _ctx(graph: Graph) -> SimpleNamespace:
    return SimpleNamespace(graph=graph)


def test_graph_provisioner_finds_existing_node():
    graph = Graph()
    existing = graph.add_node(label="door", tags={"wooden"})
    requirement = Requirement(
        graph=graph,
        identifier="door",
        policy=ProvisioningPolicy.EXISTING,
    )

    provisioner = GraphProvisioner(node_registry=graph, layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=_ctx(graph)))

    assert len(offers) == 1
    offer = offers[0]
    assert offer.operation == "EXISTING"
    assert offer.cost is ProvisionCost.DIRECT
    provider = offer.accept(ctx=_ctx(graph))
    assert provider is existing


def test_cheapest_offer_wins_existing_over_create():
    graph = Graph()
    existing = graph.add_node(label="door")
    requirement = Requirement(
        graph=graph,
        identifier="door",
        template={"obj_cls": Node, "label": "door"},
        policy=ProvisioningPolicy.ANY,
    )

    graph_prov = GraphProvisioner(node_registry=graph, layer="local")
    template_prov = TemplateProvisioner(layer="author")

    offers = []
    offers.extend(graph_prov.get_dependency_offers(requirement, ctx=_ctx(graph)))
    offers.extend(template_prov.get_dependency_offers(requirement, ctx=_ctx(graph)))

    offers.sort(key=lambda offer: offer.cost)
    best = offers[0]
    assert best.operation == "EXISTING"
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
