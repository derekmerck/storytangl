from uuid import uuid4
from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.core36.facts import Facts
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.tick import StepContext

def test_predicated_handler_uses_active_domains_true():
    g = Graph()
    root = Node(label="root", tags={"domain:dialogue"})
    scene = Node(label="scene")
    e = Edge(src_id=root.uid, dst_id=scene.uid, kind="contains")
    for it in (root, scene, e):
        (g._add_node_silent if isinstance(it, Node) else g._add_edge_silent)(it)

    facts = Facts.compute(g)
    dreg = DomainRegistry()
    dreg.add("dialogue", parents=(), provider=object())  # provider not needed for this test

    scope = Scope.assemble(g, facts, cursor_uid=scene.uid, domains=dreg)
    bus = PhaseBus()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="cx", base_hash=0)
    ctx.mount_scope(scope)

    # predicated JOURNAL handler should run because 'dialogue' is active
    bus.register_predicated(
        Phase.JOURNAL, "only-if-dialogue", 50,
        predicate=lambda c: "dialogue" in c.active_domains,
        fn=lambda c: c.say({"type":"text","text":"ok"})
    )
    bus.run(Phase.JOURNAL, ctx)
    assert any(j.get("text") == "ok" for j in ctx.journal)

def test_predicated_handler_uses_active_domains_false():
    g = Graph()
    scene = Node(label="scene")  # no domain on ancestors
    g._add_node_silent(scene)

    facts = Facts.compute(g)
    dreg = DomainRegistry()  # empty registry

    scope = Scope.assemble(g, facts, cursor_uid=scene.uid, domains=dreg)
    bus = PhaseBus()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="cy", base_hash=0)
    ctx.mount_scope(scope)

    bus.register_predicated(
        Phase.JOURNAL, "only-if-dialogue", 50,
        predicate=lambda c: "dialogue" in c.active_domains,
        fn=lambda c: c.say({"type":"text","text":"nope"})
    )
    bus.run(Phase.JOURNAL, ctx)
    assert ctx.journal == []
