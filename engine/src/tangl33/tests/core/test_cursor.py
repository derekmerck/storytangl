from types import SimpleNamespace

import pytest

from tangl33.core import Node, ContinueCap, Edge, EdgeKind, Tier, Journal, CursorDriver, Domain

def test_cursor_step_advances(graph, cap_cache, prov_reg, domain):
    root  = graph.find_one(label="root")
    next_ = Node(label="next"); graph.add(next_)
    # simple continue handler
    cap_cache.register(
        ContinueCap(lambda n, *_: Edge(src_uid=n.uid, dst_uid=next_.uid,
                                           kind=EdgeKind.CHOICE),
                        tier=Tier.NODE, owner_uid=root.uid)
    )

    journal = Journal()
    driver  = CursorDriver(graph, cap_cache, prov_reg, domain, journal)
    driver.cursor_uid = root.uid
    driver.step()
    assert driver.cursor_uid == next_.uid

def test_gather_overrides():
    from tangl33.core import Node, Graph, Domain
    graph = Graph()
    node = Node(label="node", locals={'a': 1}); graph.add(node)
    root = Node(label="root", locals={'a': 2, 'b': 3}); graph.add(root)
    node.parent_uid = root.uid
    ctx = CursorDriver._run_gather_phase(None, node, graph, Domain())
    assert ctx == {"a": 1, "b": 3}