from uuid import uuid4

import pytest

from tangl.core36 import Node, Edge
from tangl.core36 import Graph
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.execution.session import GraphSession
from tangl.persist.repo import InMemoryRepo
from tangl.persist.ser import PickleSerializer


# A. Preview + scope remount enables JOURNAL to see EXECUTE writes
def test_preview_scope_refresh_enables_domain_journal():
    g = Graph()
    # root with dialogue domain; scene as child; cursor at scene
    root = Node(label="root", tags={"domain:dialogue"})
    scene = Node(label="scene")
    e = Edge(src_id=root.uid, dst_id=scene.uid, kind="contains")
    for it in (root, scene, e):
        if isinstance(it, Node): g._add_node_silent(it)
        else: g._add_edge_silent(it)

    # example dialogue domain
    from tangl.domains.dialog import DialogueDomain

    dreg = DomainRegistry()
    dreg.add("dialogue", parents=(), provider=DialogueDomain())

    sess = GraphSession(graph_id=uuid4(),
                        graph=g,
                        repo=InMemoryRepo(),
                        serializer=PickleSerializer(),
                        domains=dreg,
                        cursor_uid=scene.uid)
    # sess.graph = g
    # sess.domains = dreg
    # sess.set_cursor(scene.uid)

    bus = PhaseBus()

    def build(ctx: StepContext):
        # ctx.refresh_scope()
        # ctx.graph = sess.graph  # supply surface
        # # mount initial (base) scope
        # facts = ctx.facts
        # scope = Scope.assemble(ctx.graph, facts, sess.cursor_uid, domains=dreg)
        # node = ctx.graph.get(sess.cursor_uid)
        # ctx.mount_scope(scope)

        # EXECUTE: create a new beat and hand off cursor, but base graph stays unchanged
        def exec_make(ctx: StepContext):
            beat = ctx.create_node("tangl.core36.entity:Node", label="beat")
            ctx.add_edge(scene.uid, beat, "contains")
            ctx.set_next_cursor(beat)
        bus.register(Phase.EXECUTE, "spawn.beat", 50, exec_make)
        bus.run(Phase.EXECUTE, ctx)

        # REFRESH from preview before JOURNAL
        ctx.refresh_scope()

        # JOURNAL: dialogue domain should run against the new cursor (beat) and say "beat: hello"
        bus.run(Phase.JOURNAL, ctx)

        print("active_domains:", ctx.scope.active_domains)
        print("journals in scope:", [h for h in ctx.scope.handlers if h[0] == Phase.JOURNAL])

    patch = sess.run_tick(choice_id="t1", build=build)

    assert any(j.get("text") == "beat: hello" for j in patch.journal), f"patch journal should have item: {patch.journal}"
    # graph now has the new beat post-commit
    assert any(isinstance(n, Node) and n.label == "beat" for n in sess.graph.items)

# B. Discourse provider sees committed + same-tick fragments (ctx.journal)
def test_sees_discourse_provider_same_tick_and_committed():
    from tangl.domains.discourse import SeesDiscourse

    g = Graph()
    beat = Node(label="beat", tags={"domain:sees_discourse"})
    g._add_node_silent(beat)

    sess = GraphSession(graph_id=uuid4(), repo=InMemoryRepo(), serializer=PickleSerializer())
    sess.graph = g
    sess.set_cursor(beat.uid)

    # mount provider
    dreg = DomainRegistry()
    dreg.add("sees_discourse", parents=(), provider=SeesDiscourse(sess.discourse))
    sess.domains = dreg

    bus = PhaseBus()
    speaker = uuid4()

    def build_once(ctx: StepContext):
        ctx.graph = sess.graph
        # initial scope on base
        facts = ctx.facts
        scope = Scope.assemble(ctx.graph, facts, sess.cursor_uid, domains=dreg)
        node = ctx.graph.get(sess.cursor_uid)
        ctx.mount_scope(scope)

        # JOURNAL handler uses discourse helpers
        def j(ctx: StepContext):
            disc = ctx.ns["discourse"]
            if not disc["has_spoken"](ctx, speaker):
                ctx.say({"text": "Intro for speaker", "speaker_uid": speaker, "tags": ["dialog_fragment"]})
            else:
                ctx.say({"text": "Follow-up", "speaker_uid": speaker, "tags": ["dialog_fragment"]})
        bus.register(Phase.JOURNAL, "disc.check", 50, j)
        bus.run(Phase.JOURNAL, ctx)

    # First tick: should introduce (committed index empty; same-tick empty at start)
    p1 = sess.run_tick(choice_id="t2", build=build_once)
    assert any("Intro" in j["text"] for j in p1.journal)

    # Second tick: committed index has the speaker, so should follow up
    p2 = sess.run_tick(choice_id="t3", build=build_once)
    assert any("Follow-up" in j["text"] for j in p2.journal)

def test_cursor_handoff_then_journal():
    g = Graph()
    root = Node(label="root", tags={"domain:dialogue"})
    scene = Node(label="scene")
    e = Edge(src_id=root.uid, dst_id=scene.uid, kind="contains")
    for it in (root, scene, e):
        (g._add_node_silent if isinstance(it, Node) else g._add_edge_silent)(it)

    # Inline dialogue domain for the test
    class DialogueDomain:
        def vars(self, g, node):
            return {"say": lambda text: {"type": "text", "text": f"{node.label}: {text}"}}
        def handlers(self, g, node):
            def journal(ctx: StepContext):
                make = ctx.ns["say"]
                ctx.say(make("hello"))
            return [(Phase.JOURNAL, "dialogue.say.hello", 50, journal)]

    dreg = DomainRegistry()
    dreg.add("dialogue", parents=(), provider=DialogueDomain())

    sess = GraphSession(graph_id=uuid4(), repo=InMemoryRepo(), serializer=PickleSerializer())
    sess.graph = g
    sess.domains = dreg
    sess.set_cursor(scene.uid)

    bus = PhaseBus()

    # TICK 1: create beat, link, and set next cursor; no journaling here
    def build_exec(ctx: StepContext):
        # base scope for current cursor
        facts = ctx.facts
        scope = Scope.assemble(ctx.graph, facts, sess.cursor_uid, domains=dreg)
        node = ctx.graph.get(sess.cursor_uid)
        ctx.mount_scope(scope)

        # EXECUTE only
        def exec_make(ctx: StepContext):
            beat = ctx.create_node("tangl.core36.entity:Node", label="beat")
            ctx.add_edge(scene.uid, beat, "contains")
            ctx.set_next_cursor(beat)  # handoff after commit
        bus.register(Phase.EXECUTE, "spawn.beat", 50, exec_make)
        bus.run(Phase.EXECUTE, ctx)

    p1 = sess.run_tick(choice_id="t1", build=build_exec)
    assert p1.journal == (), "First tick should not journal"
    assert any(isinstance(n, Node) and n.label == "beat" for n in sess.graph.items)
    assert sess.cursor_uid is not None  # moved to beat after commit

    # TICK 2: JOURNAL at the new cursor; domain handler should fire
    def build_journal(ctx: StepContext):
        facts = ctx.facts
        scope = Scope.assemble(ctx.graph, facts, sess.cursor_uid, domains=dreg)
        node = ctx.graph.get(sess.cursor_uid)
        ctx.mount_scope(scope)
        bus.run(Phase.JOURNAL, ctx)  # relies on bus picking up ctx.scope_handlers

    p2 = sess.run_tick(choice_id="t2", build=build_journal)
    assert any(j.get("text") == "beat: hello" for j in p2.journal), f"journal={p2.journal}"
