from uuid import uuid4

from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.core36 import Node, Edge, Entity, Facts, Graph

def test_inherited_domains():

    g = Graph()
    root = Node(label="root")
    scene = Node(label="scene", tags={"domain:blackjack"}, locals={"scene_var": 1})
    beat  = Node(label="beat",  locals={"local_var": 2})
    e1 = Edge(src_id=root.uid, dst_id=scene.uid, kind="contains")
    e2 = Edge(src_id=scene.uid, dst_id=beat.uid,  kind="contains")
    for it in (root, scene, beat, e1, e2):
        if isinstance(it, Node): g._add_node_silent(it)
        else: g._add_edge_silent(it)

    facts = Facts.compute(g)

    # define providers
    class InteractiveGame:
        def vars(self, g, node):
            return {"pause": lambda: {"type": "text", "text": "[paused]"}}

        def handlers(self, g, node):
            def journal(ctx: StepContext): ctx.say({"type": "text", "text": "[interactive turn]"})

            return [(Phase.JOURNAL, "ig.turn", 50, journal)]

    class Blackjack:
        def vars(self, g, node): return {"deck_size": lambda: 52}

        def handlers(self, g, node):
            def exec_(ctx: StepContext): ctx.say({"type": "text", "text": "[blackjack exec]"})

            return [(Phase.EXECUTE, "bj.exec", 50, exec_)]

    # registry
    dreg = DomainRegistry()
    dreg.add("interactive_game", parents=(), provider=InteractiveGame())
    dreg.add("blackjack", parents=("interactive_game",), provider=Blackjack())

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c", base_hash=0)
    scope = Scope.assemble(g, facts, cursor_uid=beat.uid, domains=dreg)
    ctx.mount_scope(scope)

    # ctx.ns includes pause() and deck_size()
    assert 'pause' in ctx.ns
    assert 'deck_size' in ctx.ns

    # running phases will execute ig.turn then bj.exec in order
    bus = PhaseBus()

    bus.run(Phase.EXECUTE, ctx)
    bus.run(Phase.JOURNAL, ctx)

