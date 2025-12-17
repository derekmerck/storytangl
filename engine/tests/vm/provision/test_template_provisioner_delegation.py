"""Tests ensuring template provision delegates through the world materializer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tangl.core.graph import Graph
from tangl.ir.story_ir import ActorScript, BlockScript
from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner
from tangl.vm.provision.open_edge import Dependency


def test_provisioner_delegates_to_world_materialize():
    """TemplateProvisioner should call world._materialize_from_template."""

    graph = Graph(label="test")
    template = ActorScript(label="guard", obj_cls="Actor")

    mock_world = Mock()
    mock_world.template_registry = {template.label: template}
    mock_world._materialize_from_template.return_value = Graph.add_node(
        graph, label="guard"
    )
    script_manager = Mock()
    script_manager.find_template = Mock(return_value=template)
    mock_world.script_manager = script_manager

    object.__setattr__(graph, "world", mock_world)

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    node = offers[0].accept(ctx=ctx)

    mock_world._materialize_from_template.assert_called_once()
    call_args = mock_world._materialize_from_template.call_args
    template_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("template")
    graph_arg = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("graph")
    assert template_arg.label == template.label
    assert graph_arg == graph
    assert node.label == "guard"


def test_provisioner_finds_parent_container_for_scoped_template():
    """Scoped templates should be materialized into parent container."""

    graph = Graph(label="test")
    scene = graph.add_subgraph(label="village")

    template = BlockScript(
        label="start",
        scope=ScopeSelector(parent_label="village"),
        text="Beginning",
    )

    mock_world = Mock()
    mock_world.ensure_scope = Mock(return_value=scene)

    def _materialize(*, template: BlockScript, graph: Graph, parent_container=None, **_: object):  # noqa: ANN001
        node = graph.add_node(label=template.label)
        if parent_container is not None:
            parent_container.add_member(node)
        return node

    mock_world._materialize_from_template = Mock(side_effect=_materialize)

    script_manager = Mock()
    script_manager.find_template = Mock(return_value=template)
    mock_world.script_manager = script_manager

    object.__setattr__(graph, "world", mock_world)

    requirement = Requirement(
        graph=graph,
        template_ref="village.start",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1
    node = offers[0].accept(ctx=ctx)

    mock_world.ensure_scope.assert_called_once()
    assert mock_world._materialize_from_template.call_args.kwargs["parent_container"] is scene
    assert node.parent is scene
    assert node.label == "start"


def test_provisioner_errors_if_parent_scene_missing():
    """Should error if scoped template references non-existent scene."""

    graph = Graph(label="test")

    template = BlockScript(
        label="start",
        scope=ScopeSelector(parent_label="missing_scene"),
        text="Beginning",
    )

    mock_world = Mock()
    mock_world.ensure_scope = Mock(
        side_effect=ValueError(
            "Scope requires parent container 'missing_scene' but no template found in template registry."
        )
    )
    script_manager = Mock()
    script_manager.find_template = Mock(return_value=template)
    mock_world.script_manager = script_manager

    object.__setattr__(graph, "world", mock_world)

    requirement = Requirement(
        graph=graph,
        template_ref="missing_scene.start",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    with pytest.raises(ValueError, match="no template found"):
        offers[0].accept(ctx=ctx)


def test_provisioner_normalizes_dict_templates():
    """Provisioner should normalize dict templates to BaseScriptItem."""

    graph = Graph(label="test")

    template_dict = {"label": "simple", "obj_cls": "tangl.core.graph.Node"}

    mock_world = Mock()
    mock_world.template_registry = {"simple": template_dict}
    mock_world._materialize_from_template.return_value = Graph.add_node(
        graph, label="simple"
    )
    script_manager = Mock()
    script_manager.find_template = Mock(return_value=template_dict)
    mock_world.script_manager = script_manager

    object.__setattr__(graph, "world", mock_world)

    requirement = Requirement(
        graph=graph,
        template_ref="simple",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1
    node = offers[0].accept(ctx=ctx)

    call_args = mock_world._materialize_from_template.call_args
    template_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("template")

    assert hasattr(template_arg, "model_dump")
    assert template_arg.label == "simple"
    assert node.label == "simple"


def test_provisioner_falls_back_without_world():
    """Provisioner should work without World for simple cases."""

    graph = Graph(label="test")

    template = {"label": "simple", "obj_cls": "tangl.core.graph.Node"}

    requirement = Requirement(
        graph=graph,
        template=template,
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner()
    ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    node = offers[0].accept(ctx=ctx)
    assert node.label == "simple"


def test_requirement_binding_is_explicit_not_automatic():
    """Setting req.provider should not automatically bind edge destination."""

    from tangl.story.episode.action import Action
    from tangl.story.episode.block import Block

    graph = Graph(label="test")
    block_a = Block(label="a", graph=graph)
    block_b = Block(label="b", graph=graph)

    action = Action(
        graph=graph,
        source=block_a,
        destination=None,
        content="Go to B",
    )

    req = Requirement(
        graph=graph,
        identifier="b",
        policy=ProvisioningPolicy.EXISTING,
    )

    dependency = Dependency(graph=graph, source=action, requirement=req, label="destination")

    assert dependency.destination is None

    req.provider = block_b

    assert dependency.destination == block_b
    assert action.destination is None
