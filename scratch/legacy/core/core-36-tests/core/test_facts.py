from uuid import uuid4

from tangl.core36 import Graph, Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.patch import apply_patch

def test_facts_compute_label_and_tags():
    g = Graph()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c1", base_hash=0)
    u1 = ctx.create_node("tangl.core36.entity:Node", label="hero", tags={"player","armed"})
    u2 = ctx.create_node("tangl.core36.entity:Node", label="room", tags={"place"})
    patch = ctx.to_patch(tick_id=uuid4())
    apply_patch(g, patch)

    facts = Facts.compute(g)
    assert facts.by_label("hero") == u1
    assert u1 in facts.with_tag("player")
    assert u2 in facts.with_tag("place")