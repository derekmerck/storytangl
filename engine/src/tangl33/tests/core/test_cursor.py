from types import SimpleNamespace

import pytest

from tangl33.core import Node, ContinueHandler, Edge, EdgeKind, Tier, Journal, CursorDriver

@pytest.fixture
def domain():
    return SimpleNamespace(get_globals=lambda: {})

def test_cursor_step_advances(graph, cap_cache, prov_reg, domain):
    root  = graph.find_one(label="root")
    next_ = Node(label="next"); graph.add(next_)
    # simple continue handler
    cap_cache.register(
        ContinueHandler(lambda n, *_: Edge(src_uid=n.uid, dst_uid=next_.uid,
                                           kind=EdgeKind.CHOICE),
                        tier=Tier.NODE, owner_uid=root.uid)
    )

    journal = Journal()
    driver  = CursorDriver(graph, cap_cache, prov_reg, domain, journal)
    driver.cursor_uid = root.uid
    driver.step()
    assert driver.cursor_uid == next_.uid