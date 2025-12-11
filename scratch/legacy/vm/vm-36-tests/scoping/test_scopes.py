from uuid import uuid4
from tangl.core36 import Node, Edge, Graph, Entity, Facts
from tangl.vm36.execution.patch import apply_patch
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.tick import StepContext

def test_structural_namespace_layers_and_domains():
    g = Graph()
    # Build: root -> scene -> beat (cursor), domain tag at root
    root = Node(label="root", tags={"domain:dialogue"}, locals={"greeting":"hi"})
    scene = Node(label="scene", locals={"scene_var": 1})
    beat  = Node(label="beat",  locals={"local_var": 2})
    e1 = Edge(src_id=root.uid, dst_id=scene.uid, kind="contains")
    e2 = Edge(src_id=scene.uid, dst_id=beat.uid,  kind="contains")
    for it in (root, scene, beat, e1, e2):
        if isinstance(it, Node): g._add_node_silent(it)
        else: g._add_edge_silent(it)

    facts = Facts.compute(g)

    # domain provider
    class DialogueDomain:
        def vars(self, g, node):
            return {"say": lambda text: {"type":"text","text": f'{node.label}: {text}'}}
        def handlers(self, g, node):
            def journal(ctx: StepContext):
                make = ctx.ns["say"]                      # from domain vars
                ctx.say(make(ctx.ns.get("greeting","..."))) # read structural var from root
            return [(Phase.JOURNAL, "dialogue.journal", 50, journal)]

    dreg = DomainRegistry()
    dreg.add("dialogue", provider=DialogueDomain() )

    scope = Scope.assemble(g, facts, cursor_uid=beat.uid, domains=dreg, globals_ns={"glob": 42})

    # Namespace precedence: local > scene > root > domain > globals
    assert scope.ns["local_var"] == 2
    assert scope.ns["scene_var"] == 1
    assert scope.ns["greeting"] == "hi"
    assert callable(scope.ns["say"])
    assert scope.ns["glob"] == 42

    # Mount and run JOURNAL handler
    bus = PhaseBus()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c", base_hash=0)
    ctx.mount_scope(scope)

    bus.run(Phase.JOURNAL, ctx)
    assert ctx.journal and ctx.journal[0]["text"] == "beat: hi"

    patch = ctx.to_patch(uuid4())
    print(patch)

def test_scope_overlay_runs_on_ctx_not_mutating_bus():
    g = Graph()
    # add a single node as cursor
    n = Node(label="beat", tags={'domain:toy'}, locals={"x": 1}); g._add_node_silent(n)
    assert len(g.items) == 1
    assert any(isinstance(it, Node) and it.label == "beat" for it in g.items)

    facts = Facts.compute(g)

    class ToyDomain:
        def vars(self, g, node): return {"y": 2}
        def handlers(self, g, node):
            def exec_(ctx: StepContext):
                assert ctx.ns["x"] == 1 and ctx.ns["y"] == 2
                a = ctx.create_node("tangl.core36.entity:Node", label="scoped")
            return [(Phase.EXECUTE, "toy.exec", 50, exec_)]

    dreg = DomainRegistry()
    dreg.add("toy", provider=ToyDomain())
    scope = Scope.assemble(g, facts, n.uid, domains=dreg)
    bus = PhaseBus()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c", base_hash=0)
    ctx.mount_scope(scope)

    # Global bus has no handlers, but overlay runs
    bus.run(Phase.EXECUTE, ctx)
    patch = ctx.to_patch(tick_id=uuid4()); apply_patch(g, patch)
    print( patch )
    print( "items -> ", g.items._items )
    assert len(g.items) == 2
    assert any(isinstance(it, Node) and it.label == "scoped" for it in g.items)