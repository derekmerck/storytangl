from uuid import uuid4
from tangl.vm36.execution.tick import StepContext

def test_rng_seed_makes_effects_deterministic():
    story = uuid4()
    base_hash = 123456789
    # Two contexts with identical identifiers
    c1 = StepContext(story_id=story, epoch=0, choice_id="same", base_hash=base_hash)
    c2 = StepContext(story_id=story, epoch=0, choice_id="same", base_hash=base_hash)

    # Same sequence of operations -> same UIDs in args
    a1 = c1.create_node("tangl.core36.entity:Node", label="A")
    b1 = c1.create_node("tangl.core36.entity:Node", label="B")
    e1 = c1.add_edge(a1, b1, "link")

    a2 = c2.create_node("tangl.core36.entity:Node", label="A")
    b2 = c2.create_node("tangl.core36.entity:Node", label="B")
    e2 = c2.add_edge(a2, b2, "link")

    p1 = c1.to_patch(uuid4()); p2 = c2.to_patch(uuid4())
    # seeds equal
    assert p1.rng_seed == p2.rng_seed
    # effects equal (op + args)
    assert [(e.op, e.args) for e in p1.effects] == [(e.op, e.args) for e in p2.effects]