"""Tests for TemplateProvisioner template_ref handling."""

from __future__ import annotations

from tangl.core.graph import Graph, Node
from tangl.core.registry import Registry
from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.vm.provision import (
    ProvisioningContext,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


def _ctx(graph: Graph) -> ProvisioningContext:
    return ProvisioningContext(graph=graph, step=0)


def test_template_provisioner_offers_for_template_ref_in_mapping() -> None:
    graph = Graph(label="story")
    requirement = Requirement(
        graph=graph,
        template_ref="guard_template",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(
        template_registry={
            "guard_template": {"label": "guard", "obj_cls": Node}
        },
        layer="author",
    )

    ctx = _ctx(graph)
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == "guard"
    assert provider in graph


def test_template_provisioner_uses_registry_lookup_for_template_ref() -> None:
    graph = Graph(label="story")
    registry: Registry[ActorScript] = Registry(label="templates")
    actor_template = ActorScript.model_validate(
        {
            "label": "village.guard",
            "obj_cls": "tangl.story.concepts.actor.actor.Actor",
        }
    )
    registry.add(actor_template)

    requirement = Requirement(
        graph=graph,
        template_ref=actor_template.label,
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(template_registry=registry, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    provider = offers[0].accept(ctx=ctx)
    assert provider.label == actor_template.label
    assert provider in graph


def test_template_provisioner_skips_unknown_template_ref() -> None:
    graph = Graph(label="story")
    requirement = Requirement(
        graph=graph,
        template_ref="missing.template",
        policy=ProvisioningPolicy.CREATE,
    )

    provisioner = TemplateProvisioner(template_registry={}, layer="author")
    ctx = _ctx(graph)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert offers == []
