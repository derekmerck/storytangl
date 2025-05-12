from types import SimpleNamespace

import pytest

from tangl33.core import Node, ContinueCap, Edge, EdgeKind, Tier, Journal, CursorDriver, Domain

@pytest.mark.skip(reason="deprecated")
def test_cursor_step_advances(graph, domain):
    root  = graph.find_one(label="root")
    next_ = Node(label="next"); graph.add(next_)
    # simple continue handler
    continue_cap = ContinueCap(lambda n, *_: Edge(src_uid=n.uid, dst_uid=next_.uid,
                                           kind=EdgeKind.CHOICE),
                                           tier=Tier.NODE, owner_uid=root.uid)
    domain.handler_layer("choice").append(continue_cap)

    journal = Journal()
    driver  = CursorDriver(graph, domain, journal)
    driver.cursor_uid = root.uid
    driver.step()
    assert driver.cursor_uid == next_.uid
