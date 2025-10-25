from uuid import uuid4
from tangl.core36 import Graph
from tangl.vm36.execution import StepContext, apply_patch

def test_add_and_delete_edge_by_id():
    g = Graph()

    # tick 1: create two nodes + edge
    t1 = StepContext(story_id=uuid4(), epoch=0, choice_id="t1", base_hash=0)
    a = t1.create_node("tangl.core36.entity:Node", label="A")
    b = t1.create_node("tangl.core36.entity:Node", label="B")
    e = t1.add_edge(a, b, "link")
    apply_patch(g, t1.to_patch(tick_id=uuid4()))

    # sanity
    ids = g.find_edge_ids(src=a, dst=b, kind="link")
    assert e in ids and len(ids) == 1

    # tick 2: delete it
    t2 = StepContext(story_id=uuid4(), epoch=1, choice_id="t2", base_hash=0)
    t2.del_edge(e)
    apply_patch(g, t2.to_patch(tick_id=uuid4()))

    assert len(list(g.edges())) == 0