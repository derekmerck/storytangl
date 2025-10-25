import pathlib

from pyrsistent import pmap, pvector
import pytest

from tangl.core35.model import StoryIR, Shape, Patch, Op, Node, Edge
from tangl.core35.io import snapshot, restore, PatchLogWriter, PatchLogReader, apply_patch
from tangl.core35.engine import step
from tangl.core35.behaviors.default_behaviors import noop_behaviors, stub_behaviors
from tangl.core35.behaviors.behavior_registry import _NOOP_BEHAVIOR
from .scope import ScopeMeta, ScopeTree, ScopeManager, Layer, LayerStack, build_scope_tree
from tangl.core35.context import Context

def test_patchlog_roundtrip_mock_reader(tmp_path):
    ir0 = StoryIR(shape=Shape())
    patch = Patch(tick=1, op=Op.SET,
                  path=("state","hp"), before=None, after=100)

    # Mutation (in-place replacement for S-0 demo)
    ir1 = ir0.__class__(shape=ir0.shape,
                        state=ir0.state.set("hp",100),
                        layer_stack=ir0.layer_stack,
                        tick=1)

    # Write snapshot & patch log
    snap = snapshot(ir0)
    log  = tmp_path/"run.patchlog"
    with log.open("wb") as fp:
        writer = PatchLogWriter(fp)
        writer.append(patch)
        writer.close()

    # Restore
    ir_r = restore(snap)
    # Re-apply patches (toy)
    assert ir_r.state == pmap()
    ir_r = ir_r.__class__(shape=ir_r.shape,
                          state=ir_r.state.set("hp",100),
                          layer_stack=ir_r.layer_stack,
                          tick=1)
    assert ir_r == ir1


def test_patchlog_roundtrip(tmp_path: pathlib.Path):
    # empty IR
    ir0 = StoryIR(shape=Shape())

    # simple SET-state patch
    patch = Patch(
        tick=1,
        op=Op.SET,
        path=("state","hp"),
        before=None,
        after=42
    )

    # --- write snapshot & log ---
    snap = snapshot(ir0)
    log_file = tmp_path / "run.patchlog"
    with log_file.open("wb") as fp:
        w = PatchLogWriter(fp); w.append(patch); w.close()

    # --- restore & replay ---
    ir = restore(snap)
    with log_file.open("rb") as fp:
        for p in PatchLogReader(fp):
            ir = apply_patch(ir, p)

    assert ir.state["hp"] == 42
    assert ir.tick == 1


def test_phase_runner_noop():
    ir = StoryIR()                          # empty but valid
    ir2, patches = step(ir, noop_behaviors)
    assert ir2.layer_stack == ir.layer_stack and ir2.state == ir.state
    # tick has changed though, so we can't just compare ir2 == ir
    assert patches == []


def test_layer_shadowing():
    # Build fake scopes root -> scene -> mini
    tree = ScopeTree({
        "root": ScopeMeta("root", None),
        "scene": ScopeMeta("scene", "root"),
        "mini": ScopeMeta("mini", "scene")
    })
    stack = LayerStack()
    mgr   = ScopeManager(tree, stack)

    # Push root manually
    stack.push(Layer(scope_id="root"))

    # define a dummy behaviour
    def hello(ir): return ir, []
    def shadow(ir): return ir, []

    # root has default registry (empty)
    assert stack.lookup_behavior("hello") is _NOOP_BEHAVIOR

    def stack_layers():
        return [layer.scope_id for layer in stack._stack]

    assert stack_layers() == ["root"], f"Stack layers {stack_layers()} should have ['root']"

    # switch to scene
    mgr.switch("root", "scene")
    assert stack_layers() == ["root", "scene"], f"Stack layers {stack_layers()} should have ['root', 'scene']"
    stack.top().behaviors.register("hello")(hello)
    assert stack.lookup_behavior("hello") is hello

    # switch to mini and override
    mgr.switch("scene", "mini")
    assert stack_layers() == ["root", "scene", "mini"], f"Stack layers {stack_layers()} should have ['root', 'scene', 'mini']"
    assert stack.top().scope_id == "mini", "Top should be mini"
    stack.top().behaviors.register("hello")(shadow)
    assert stack.top().behaviors._store["hello"][0][1] is shadow, "Mini should have shadow"
    assert stack.lookup_behavior("hello") is shadow, f"Behavior for {stack_layers()} should be shadow"

    # pop back to root
    mgr.switch("mini", "root")
    assert stack_layers() == ["root"], f"Stack layers {stack_layers()} should have ['root']"
    print(stack_layers())
    # assert stack.lookup_behavior("hello") is _NOOP_BEHAVIOUR

def test_lookup_var_shadow():
    stack = LayerStack()
    stack.push(Layer("root", locals=pmap({"x": 1})))
    stack.push(Layer("child", locals=pmap({"y": 2})))

    view = Context(None, stack, pmap({"z": 3}), tick=-1)
    assert view.var("y") == 2      # found in child
    assert view.var("x") == 1      # falls through to root
    assert view.var("z") == 3     # global
    with pytest.raises(KeyError):
        _ = view.var("missing")

    # getitem accessor
    assert view.vars["y"] == 2


def test_context_setter():
    stack = LayerStack()
    stack.push(Layer("root"))
    ctx = Context(None, stack, pmap(), tick=0)

    ctx2, p = ctx.set_var("player.hp", 100)
    assert ctx2.var("player.hp") == 100
    assert p.path == ("state", "player.hp") or p.path[0] == "layer"

def test_two_tick_traversal(tmp_path):
    # --- Build toy graph ----------
    root  = Node(id="n_root",  scope_id="root")
    scene = Node(id="n_scene", scope_id="scene")
    mini  = Node(id="n_mini",  scope_id="mini")

    e1 = Edge("e1", "n_root", "n_scene", "true")
    e2 = Edge("e2", "n_scene", "n_mini", "true")
    root.outgoing = (e1,)
    scene.outgoing = (e2,)

    shape = Shape(nodes=pmap({n.id: n for n in (root, scene, mini)}),
                  edges=pvector([e1, e2]))

    # ir0 = StoryIR(shape=shape, state=pmap({
    #     "cursor": "n_root",
    #     # convenient back-refs so behaviors can ctx.var("n_root.node")
    #     "n_root.node":  root,
    #     "n_scene.node": scene,
    #     "n_mini.node":  mini,
    # }))

    ir0 = StoryIR(
        shape=shape,
        state=pmap({
            "cursor": "n_root",
            # "n_root": pmap({"node": root}),
            # "n_scene": pmap({"node": scene}),
            # "n_mini": pmap({"node": mini}),
        })
    )

    # --- Prime stack with root layer & scope manager ----
    tree = build_scope_tree(shape.nodes)
    ir0.layer_stack.scope_manager = ScopeManager(tree=tree, stack=ir0.layer_stack)
    ir0.layer_stack.push(Layer("root"))
    # stack = LayerStack()
    # stack.push(Layer("root"))
    # stack.scope_manager = ScopeManager(tree, stack)   # quick and dirty
    # ir0 = ir0.evolve(layer_stack=stack)  # attach the primed stack

    # --- Run two ticks --------------
    ir1, p1 = step(ir0, stub_behaviors)        # root -> scene
    assert len(p1) > 0
    assert any(p.path == ("state", "cursor") for p in p1), f"state.cursor should be in a patch ({p1})"

    ir2, p2 = step(ir1, stub_behaviors)        # scene -> mini
    assert any(p.path == ("state", "cursor") and p.after == "n_mini" for p in p2)

    # --- Snapshot + patchlog -------
    snap = snapshot(ir0)
    with open(tmp_path/"log", "wb") as fp:
        w = PatchLogWriter(fp); [w.append(x) for x in (*p1,*p2)]; w.close()

    # --- Restore & replay ----------
    ir_r = restore(snap)
    with open(tmp_path/"log","rb") as fp:
        for patch in PatchLogReader(fp):
            ir_r = apply_patch(ir_r, patch)

    # assert ir_r == ir2
    assert ir_r.state["cursor"] == "n_mini", f"Cursor {ir_r.state['cursor']} should be n_mini"
    assert ir_r.state["visited.mini"] is True, f"mini.visited should be True"
