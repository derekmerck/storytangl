from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from tangl.core.graph import Graph, Node
from tangl.core.registry import Registry
from tangl.ir.core_ir.base_script_model import BaseScriptItem
from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.vm.context import Context
from tangl.vm.provision import (
    ProvisioningContext,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


def _ctx(graph: Graph, cursor: Node | None = None):
    if cursor is None:
        return ProvisioningContext(graph=graph, step=0)
    return Context(graph=graph, cursor_id=cursor.uid, step=0)


def test_template_provisioner_reads_world_registry() -> None:
    graph = Graph(label="story")
    registry: Registry[BaseScriptItem] = Registry(label="templates")
    graph.add_subgraph(label="town")
    graph.add_subgraph(label="castle")
    registry.add(BaseScriptItem(label="villager"))

    provider = Node(label="villager", graph=graph)
    world = Mock()
    world.template_registry = registry
    world._materialize_from_template.return_value = provider
    object.__setattr__(graph, "world", world)

    requirement = Requirement(
        graph=graph,
        template_ref="villager",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "villager"
    assert provider in graph


def test_template_rejected_when_out_of_scope() -> None:
    graph = Graph(label="story")
    town = graph.add_subgraph(label="town", tags={"town"})
    block = graph.add_node(label="block")
    town.add_member(block)

    registry: Registry[BaseScriptItem] = Registry(label="templates")
    registry.add(
        BaseScriptItem(
            label="guard",
            scope=ScopeSelector(ancestor_tags={"city"}),
        )
    )
    object.__setattr__(graph, "world", SimpleNamespace(template_registry=registry))

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph, block)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_template_selected_when_in_scope() -> None:
    graph = Graph(label="story")
    town = graph.add_subgraph(label="town", tags={"town"})
    block = graph.add_node(label="block")
    town.add_member(block)

    registry: Registry[BaseScriptItem] = Registry(label="templates")
    registry.add(
        BaseScriptItem(
            label="guard",
            scope=ScopeSelector(ancestor_tags={"town"}),
        )
    )
    object.__setattr__(graph, "world", SimpleNamespace(template_registry=registry))

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph, block)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "guard"
    assert provider in graph


def test_template_provisioner_falls_back_to_local_registry() -> None:
    graph = Graph(label="story")
    registry: Registry[BaseScriptItem] = Registry(label="templates")
    registry.add(BaseScriptItem(label="hermit"))

    requirement = Requirement(
        graph=graph,
        template_ref="hermit",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(template_registry=registry, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    assert offers[0].accept(ctx=ctx).label == "hermit"


def test_template_ref_accepts_qualified_identifier() -> None:
    graph = Graph(label="story")
    registry: Registry[BaseScriptItem] = Registry(label="templates")
    registry.add(
        BaseScriptItem(label="start", scope=ScopeSelector(parent_label="scene1"))
    )

    object.__setattr__(graph, "world", SimpleNamespace(template_registry=registry))

    requirement = Requirement(
        graph=graph,
        template_ref="scene1.start",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "start"


def test_bare_template_ref_uses_scope_hint() -> None:
    graph = Graph(label="story")
    graph.add_subgraph(label="town")
    graph.add_subgraph(label="castle")
    registry: Registry[BaseScriptItem] = Registry(label="templates")
    town_guard = BaseScriptItem(
        label="guard",
        scope=ScopeSelector(parent_label="town"),
    )
    castle_guard = BaseScriptItem(
        label="guard",
        scope=ScopeSelector(parent_label="castle"),
    )
    registry.add(town_guard)
    registry.add(castle_guard)

    world = Mock()
    world.template_registry = registry
    world._materialize_from_template.side_effect = lambda template, graph, parent_container=None: Node(
        label=template.label, graph=graph
    )

    object.__setattr__(graph, "world", world)

    requirement = Requirement(
        graph=graph,
        identifier="town.guard",
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "guard"

    # Ensure scoped template was chosen
    world._materialize_from_template.assert_called_once()
    chosen_template = world._materialize_from_template.call_args.kwargs["template"]
    assert chosen_template.scope.parent_label == "town"
