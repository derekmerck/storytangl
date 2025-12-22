"""Tests ensuring template provision uses factory materialization."""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core.factory import TemplateFactory, Template
from tangl.core.graph import Graph, Node, Subgraph
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


def _ctx(graph: Graph) -> SimpleNamespace:
    return SimpleNamespace(graph=graph, cursor=None, cursor_id=None)


def test_provisioner_materializes_template_from_factory() -> None:
    graph = Graph(label="test")
    factory = TemplateFactory(label="templates")
    factory.add(Template[Node](label="guard", tags={"npc"}))

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(factory=factory, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    node = offers[0].accept(ctx=ctx)

    assert node.label == "guard"
    assert "npc" in node.tags
    assert node in graph


def test_provisioner_materializes_template_from_requirement() -> None:
    graph = Graph(label="test")

    requirement = Requirement(
        graph=graph,
        template=Template[Node](label="simple", tags={"core"}),
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    node = offers[0].accept(ctx=ctx)

    assert node.label == "simple"
    assert "core" in node.tags
    assert node in graph


def test_provisioner_supports_subgraph_templates() -> None:
    graph = Graph(label="test")
    factory = TemplateFactory(label="templates")
    factory.add(Template[Subgraph](label="village", obj_cls=Subgraph))

    requirement = Requirement(
        graph=graph,
        template_ref="village",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(factory=factory, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    subgraph = offers[0].accept(ctx=ctx)

    assert isinstance(subgraph, Subgraph)
    assert subgraph.label == "village"
    assert subgraph in graph
