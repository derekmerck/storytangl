from types import SimpleNamespace

from tangl.core.graph.graph import Graph
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


def test_template_provisioner_skips_out_of_scope_registry_templates() -> None:
    template_registry = {
        "late_actor": {
            "label": "late_actor",
            "scope": {"parent_label": "elsewhere"},
            "obj_cls": "tangl.story.concepts.actor.actor.Actor",
        }
    }

    graph = Graph(label="scope_graph")
    intro_scope = SimpleNamespace(label="intro", parent=None)
    cursor = SimpleNamespace(label="start", parent=intro_scope)
    ctx = SimpleNamespace(graph=graph, cursor=cursor, cursor_id=None)

    requirement = Requirement(
        graph=graph,
        template_ref="late_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    provisioner = TemplateProvisioner(template_registry=template_registry, layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert offers == []


def test_template_provisioner_matches_registry_scope_by_ancestor_tags_mapping() -> None:
    template_registry = {
        "branch_actor": {
            "label": "branch_actor",
            "scope": {"ancestor_tags": ["branch"]},
            "obj_cls": "tangl.story.concepts.actor.actor.Actor",
        }
    }

    graph = Graph(label="scope_graph")
    root_scope = SimpleNamespace(label="intro", tags={"branch"}, parent=None)
    cursor = SimpleNamespace(label="start", tags=set(), parent=root_scope)
    ctx = SimpleNamespace(graph=graph, cursor=cursor, cursor_id=None)

    requirement = Requirement(
        graph=graph,
        template_ref="branch_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )

    provisioner = TemplateProvisioner(template_registry=template_registry, layer="local")
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

    assert len(offers) == 1
