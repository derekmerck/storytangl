from uuid import uuid4

from tangl.core.graph import Graph, Subgraph, Node
from tangl.core.factory import Template
from tangl.vm.provision import (
    GraphProvisioner,
    TemplateProvisioner,
    Requirement,
    ProvisioningPolicy,
    ProvisionCost,
)
from tangl.vm.provision.resolver import ProvisioningContext


def _make_scene(graph: Graph, label: str) -> Subgraph:
    return graph.add_subgraph(label=label)


def test_graph_provisioner_calculates_proximity_costs() -> None:
    graph = Graph()
    source = graph.add_node(label="source")
    same_scene = graph.add_node(label="scene-npc")
    other_scene = graph.add_node(label="other-scene-npc")
    remote = graph.add_node(label="remote")

    episode = _make_scene(graph, "episode")
    scene_a = _make_scene(graph, "scene-a")
    scene_b = _make_scene(graph, "scene-b")
    episode.add_member(scene_a)
    episode.add_member(scene_b)
    scene_a.add_member(source)
    scene_a.add_member(same_scene)
    scene_b.add_member(other_scene)

    remote_episode = _make_scene(graph, "remote")
    remote_episode.add_member(remote)

    provisioner = GraphProvisioner(node_registry=graph)
    ctx = ProvisioningContext(graph=graph, step=1)

    def _offer_for(target: Node, *, src: Node) -> float:
        requirement = Requirement(
            graph=graph,
            identifier=target.uid,
            policy=ProvisioningPolicy.EXISTING,
        )
        ctx.current_requirement_source_id = src.uid
        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
        assert offers, "expected a proximity offer"
        return offers[0]

    same_node_offer = _offer_for(source, src=source)
    assert same_node_offer.proximity == 0.0
    assert same_node_offer.cost == float(ProvisionCost.DIRECT)
    assert same_node_offer.proximity_detail == "same block"

    same_scene_offer = _offer_for(same_scene, src=source)
    assert same_scene_offer.proximity == 5.0
    assert same_scene_offer.cost == float(ProvisionCost.DIRECT) + 5.0
    assert same_scene_offer.proximity_detail == "same scene"

    same_episode_offer = _offer_for(other_scene, src=source)
    assert same_episode_offer.proximity == 10.0
    assert same_episode_offer.cost == float(ProvisionCost.DIRECT) + 10.0
    assert same_episode_offer.proximity_detail == "same episode"

    distant_offer = _offer_for(remote, src=source)
    assert distant_offer.proximity == 20.0
    assert distant_offer.cost == float(ProvisionCost.DIRECT) + 20.0
    assert distant_offer.proximity_detail == "distant"


def test_graph_provisioner_skips_template_references() -> None:
    graph = Graph()
    source = graph.add_node(label="source")
    target = graph.add_node(label="templated")
    requirement = Requirement(
        graph=graph,
        identifier=target.uid,
        template_ref="npc.guard",
        policy=ProvisioningPolicy.ANY,
    )
    ctx = ProvisioningContext(graph=graph, step=2)
    ctx.current_requirement_source_id = source.uid
    provisioner = GraphProvisioner(node_registry=graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert offers == []


def test_template_provisioner_uses_fixed_create_cost() -> None:
    graph = Graph()
    requirement = Requirement(
        graph=graph,
        template=Template[Node](label="fabricated", obj_cls=Node),
        policy=ProvisioningPolicy.CREATE,
    )
    ctx = ProvisioningContext(graph=graph, step=3)
    provisioner = TemplateProvisioner(factory=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1
    offer = offers[0]
    assert offer.cost == float(ProvisionCost.CREATE)
    assert offer.proximity_detail == "new instance"
