from uuid import uuid4

from tangl.vm36.execution.session import GraphSession
from tangl.persist.repo import InMemoryRepo
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.patch import resolve_fqn  # used by session loader if you call it

def resolver(fqn: str):  # for GraphSession.load_or_init if you use it later
    return resolve_fqn(fqn)

def test_session_tick_with_three_phases():
    sess = GraphSession(graph_id=uuid4(), repo=InMemoryRepo())

    def build(ctx):
        bus = PhaseBus()
        # validate: no-op
        bus.register(Phase.VALIDATE, "guards", 50, lambda c: None)
        # execute: create two nodes + edge
        def exec_(c):
            a = c.create_node("tangl.core36.entity:Node", label="A")
            b = c.create_node("tangl.core36.entity:Node", label="B")
            c.add_edge(a, b, "link")
        bus.register(Phase.EXECUTE, "spawn", 50, exec_)
        # journal
        bus.register(Phase.JOURNAL, "narr", 50, lambda c: c.say({"type":"text","text":"A→B"}))
        # run
        bus.run(Phase.VALIDATE, ctx); bus.run(Phase.EXECUTE, ctx); bus.run(Phase.JOURNAL, ctx)

    patch = sess.run_tick(choice_id="choice-1", build=build)

    # Graph should contain two nodes and one edge after apply
    nodes = [it for it in sess.graph.items if it.__class__.__name__ == "Node"]
    edges = [it for it in sess.graph.items if it.__class__.__name__ == "Edge"]
    assert len(nodes) == 2
    assert len(edges) == 1
    assert len(patch.journal) == 1