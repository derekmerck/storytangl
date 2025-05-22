import pytest

from tangl34.core.driver import CursorDriver
from tangl34.core.structure import Node, Graph, EdgeKind
from tangl34.core.journal import HasJournal

def test_cursor_driver_guard_rail_on_choice():

    r = Node(label="root")
    n = Node(label="test")
    g = Graph()
    g.add(n)
    g.add(r)
    e = g.add_edge(r, n, edge_kind=EdgeKind.ASSOCIATE)
    j = HasJournal()
    drv = CursorDriver(cursor=n, graph=g, journal=j, scopes=[])
    with pytest.raises(RuntimeError):
        drv.advance_cursor(choice=e)

def test_cursor_driver_advance():
    # Patch service calls to record order
    call_order = []

    r = Node(label="root")
    n = Node(label="test")
    g = Graph()
    g.add(n)
    g.add(r)
    e = g.add_edge(r, n, edge_kind=EdgeKind.CHOICE)
    j = HasJournal()
    drv = CursorDriver(cursor=n, graph=g, journal=j, scopes=[])
    drv.advance_cursor(choice=e)
