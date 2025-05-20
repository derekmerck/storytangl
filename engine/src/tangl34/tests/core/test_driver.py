from tangl34.core.driver import CursorDriver
from tangl34.core.structure import Node, Graph
from tangl34.core.journal import HasJournal


def test_cursor_driver_advance():
    # Patch service calls to record order
    call_order = []

    r = Node(label="root")
    n = Node(label="test")
    g = Graph()
    g.add(n)
    g.add(r)
    e = g.add_edge(r, n)
    j = HasJournal()
    drv = CursorDriver(cursor=n, graph=g, journal=j, scopes=[])
    drv.advance_cursor(choice=e)