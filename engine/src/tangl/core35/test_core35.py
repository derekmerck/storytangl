import pathlib

from pyrsistent import pmap, pvector
import pytest

from tangl.core35.model import StoryIR, Shape, Patch, Op, Node, Edge
from tangl.core35.io import snapshot, restore, PatchLogWriter, PatchLogReader, apply_patch
from tangl.core35.engine import step
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
    from tangl.core35.behaviors.default_behaviors import behaviors
    ir2, patches = step(ir, behaviors)
    assert ir2 == ir
    assert patches == []

from .scope import ScopeMeta, ScopeTree, ScopeManager, Layer, LayerStack
from tangl.core35.behaviors.behavior_registry import _NOOP_BEHAVIOR

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

    view = Context(stack, pmap({"z": 3}), tick=-1)
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
    ctx = Context(stack, pmap(), tick=0)

    ctx2, p = ctx.set_var("player.hp", 100)
    assert ctx2.var("player.hp") == 100
    assert p.path == ("state", "player.hp") or p.path[0] == "layer"

@pytest.fixture
def graph_ir():
    root = Node(id="n_root", scope_id="root")
    scene = Node(id="n_scene", scope_id="scene")
    mini = Node(id="n_mini", scope_id="mini")

    e1 = Edge(id="e1", src="n_root", dst="n_scene", predicate="true")
    e2 = Edge(id="e2", src="n_scene", dst="n_mini", predicate="true")

    shape = Shape(nodes=pmap({n.id: n for n in (root, scene, mini)}),
                  edges=pvector([e1, e2]))
    ir0 = StoryIR(shape=shape)
    return ir0

def test_pred(graph_ir):
    ...