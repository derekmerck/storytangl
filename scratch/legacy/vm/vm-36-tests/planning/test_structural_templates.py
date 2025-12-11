from uuid import uuid4

from tangl.core36.graph import Graph, Node
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.frontier import discover_frontier

def test_structural_templates_flow_into_frontier():
    g = Graph()
    scene = Node(label="scene", locals={"templates": [
        {"id": "inspect", "label": "Inspect", "requires": []},
    ]})
    g._add_node_silent(scene)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t1", base_hash=0, graph=g)
    facts = Facts.compute(g)
    scope = Scope.assemble(g, facts, scene.uid, domains=None)
    ctx.mount_scope(scope)

    choices = discover_frontier(ctx, anchor_uid=scene.uid)
    assert {(c.id, c.status) for c in choices} == {("inspect", "enabled")}