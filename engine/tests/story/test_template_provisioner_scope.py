from types import SimpleNamespace

from tangl.core.factory import TemplateFactory
from tangl.core.graph.graph import Graph
from tangl.ir.core_ir import BaseScriptItem
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


def test_template_provisioner_skips_out_of_scope_registry_templates() -> None:
    factory = TemplateFactory(label="scope_factory")
    factory.add(
        BaseScriptItem(
            label="late_actor",
            obj_cls="tangl.story.concepts.actor.actor.Actor",
            path_pattern="elsewhere.*",
        )
    )

    graph = Graph(label="scope_graph")
    cursor = graph.add_node(label="start")
    graph.add_subgraph(label="intro", members=[cursor])
    object.__setattr__(graph, "factory", factory)
    ctx = SimpleNamespace(graph=graph, cursor=cursor, cursor_id=None)

    requirement = Requirement(
        graph=graph,
        template_ref="late_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    assert factory.find_one(identifier="late_actor", selector=cursor) is None

    provisioner = TemplateProvisioner(layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_template_provisioner_matches_registry_scope_by_ancestor_tags_mapping() -> None:
    factory = TemplateFactory(label="scope_factory")
    factory.add(
        BaseScriptItem(
            label="branch_actor",
            obj_cls="tangl.story.concepts.actor.actor.Actor",
            ancestor_tags={"branch"},
        )
    )

    graph = Graph(label="scope_graph")
    cursor = graph.add_node(label="start")
    graph.add_subgraph(label="intro", members=[cursor], tags={"branch"})
    object.__setattr__(graph, "factory", factory)
    ctx = SimpleNamespace(graph=graph, cursor=cursor, cursor_id=None)

    requirement = Requirement(
        graph=graph,
        template_ref="branch_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    assert factory.find_one(identifier="branch_actor", selector=cursor) is not None

    provisioner = TemplateProvisioner(layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
