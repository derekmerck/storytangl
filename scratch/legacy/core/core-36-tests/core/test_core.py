# tangl/tests/test_patch.py
from uuid import uuid4
from tangl.core import Node, Graph
# from tangl.vm36.execution import StepContext, apply_patch


def test_create_node_and_set_attr():
    g = Graph()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c1", base_hash=0, graph=g)
    uid = ctx.create_node("tangl.core36.entity:Node", label="hero")
    ctx.set_attr(uid, ("tags",), {"player"})
    patch = ctx.to_patch(tick_id=uuid4())
    apply_patch(g, patch)
    e = g.get(uid); assert isinstance(e, Node)
    assert e.label == "hero"
    assert e.tags == {"player"}
