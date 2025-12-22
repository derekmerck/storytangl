from __future__ import annotations

from types import SimpleNamespace

from pydantic import Field

from tangl.core.factory import Factory, HierarchicalTemplate
from tangl.core.graph import Graph, Node
from tangl.vm.provision import (
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


def _ctx(graph: Graph, cursor: Node | None = None) -> SimpleNamespace:
    cursor_id = cursor.uid if cursor is not None else None
    return SimpleNamespace(graph=graph, cursor=cursor, cursor_id=cursor_id)


class SceneTemplate(HierarchicalTemplate[Node]):
    guards: dict[str, HierarchicalTemplate[Node]] = Field(
        default_factory=dict,
        json_schema_extra={"visit_field": True},
    )


def _build_factory() -> Factory:
    root = HierarchicalTemplate[Node](
        label="world",
        children={
            "town": SceneTemplate(
                label="town",
                guards={
                    "guard": HierarchicalTemplate[Node](
                        label="guard",
                        obj_cls=Node,
                        tags={"town"},
                    ),
                },
            ),
            "castle": SceneTemplate(
                label="castle",
                guards={
                    "guard": HierarchicalTemplate[Node](
                        label="guard",
                        obj_cls=Node,
                        tags={"castle"},
                    ),
                },
            ),
        },
    )
    return Factory.from_root_templ(root)


def _build_graph() -> tuple[Graph, Node, Node]:
    graph = Graph(label="story")
    world = graph.add_subgraph(label="world")
    town = graph.add_subgraph(label="town")
    castle = graph.add_subgraph(label="castle")
    world.add_member(town)
    world.add_member(castle)

    town_block = graph.add_node(label="block")
    town.add_member(town_block)

    castle_block = graph.add_node(label="block")
    castle.add_member(castle_block)

    return graph, town_block, castle_block


def test_template_provisioner_matches_scoped_template() -> None:
    factory = _build_factory()
    graph, town_block, _ = _build_graph()

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(factory=factory, layer="author")
    ctx = _ctx(graph, town_block)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "guard"
    assert "town" in provider.tags


def test_template_provisioner_rejects_out_of_scope_template() -> None:
    factory = _build_factory()
    graph = Graph(label="story")
    outsider = graph.add_node(label="outsider")

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(factory=factory, layer="author")
    ctx = _ctx(graph, outsider)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_template_ref_accepts_qualified_identifier() -> None:
    factory = _build_factory()
    graph, _, _ = _build_graph()

    requirement = Requirement(
        graph=graph,
        template_ref="world.town.guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(factory=factory, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "guard"
    assert "town" in provider.tags
