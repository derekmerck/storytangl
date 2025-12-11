from uuid import uuid4
from random import shuffle
from tangl.vm36.execution.patch import  Effect, Op, Patch, canonicalize, apply_patch
from tangl.core36.graph import Graph

def test_canonicalize_random_order_results_in_same_graph():
    g1 = Graph(); g2 = Graph()
    # Build the same effect set
    n1 = uuid4(); n2 = uuid4(); eid = uuid4()
    cls = "tangl.core36.entity:Node"

    effects = [
        Effect(Op.CREATE_NODE, (n1, cls, {"label":"A"})),
        Effect(Op.CREATE_NODE, (n2, cls, {"label":"B"})),
        Effect(Op.ADD_EDGE,    (n1, n2, "link", eid)),
        Effect(Op.SET_ATTR,    (n1, ("tags",), {"t"})),
        Effect(Op.DEL_EDGE,    (eid,)),
    ]
    randomized = effects[:]; shuffle(randomized)

    # Apply randomized (apply_patch calls canonicalize internally)
    apply_patch(g1, Patch(uuid4(), 0, tuple(randomized)))
    # Apply canonical order explicitly
    apply_patch(g2, Patch(uuid4(), 0, tuple(canonicalize(effects))))

    assert g1.to_dto() == g2.to_dto()