# tests/test_templates_structural_scope.py
from uuid import uuid4

from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.vm36.execution.tick import StepContext
from tangl.domains.structural_templates import StructuralTemplates
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning import ProvisionRequirement, discover_frontier


def test_scene_local_template_exposed_to_child_cursor():
    g = Graph()
    scene = Node(label="scene", locals={
        "templates": [
            {"id":"inspect", "label":"Inspect", "requires":[ProvisionRequirement(kind="entity", name="torch", constraints={}, policy={"optional":True})]}
        ]
    })
    beat = Node(label="beat")
    g._add_node_silent(scene); g._add_node_silent(beat)
    g._add_edge_silent(Edge(src_id=scene.uid, dst_id=beat.uid, kind="contains"))

    dreg = DomainRegistry()
    dreg.add("struct", provider=StructuralTemplates())  # makes templates() available

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t", base_hash=0, graph=g)
    scope = Scope.assemble(g, ctx.facts, cursor_uid=beat.uid, domains=dreg)
    ctx.mount_scope(scope)

    choices = discover_frontier(ctx, anchor_uid=beat.uid)
    ids = {c.id for c in choices}
    assert "inspect" in ids
