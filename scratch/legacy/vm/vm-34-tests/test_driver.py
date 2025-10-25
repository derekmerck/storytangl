import pytest

from tangl.core.entity import Graph, Node
from tangl.core.solver import HasJournal, ChoiceEdge
from tangl.core.solver.forward_resolve import ForwardResolver

def test_cursor_driver_guard_rail_on_choice():
    g = Graph()
    r = Node(label="root", graph=g)
    n = Node(label="test", graph=g)
    e = g.add_edge(r, n)
    j = HasJournal()
    drv = ForwardResolver(cursor_id=r.uid, graph=g, journal=j, scopes=[])
    with pytest.raises(TypeError):
        drv.resolve_choice(e)

@pytest.mark.xfail(raises=AttributeError)
def test_cursor_driver_advance():
    g = Graph()
    r = Node(label="root", graph=g)
    n = Node(label="test", graph=g)
    e = ChoiceEdge(src_id=r.uid, dest_id=n.uid, graph=g)
    j = HasJournal()
    drv = ForwardResolver(cursor_id=r.uid, graph=g, journal=j, scopes=[])
    drv.resolve_choice(e)
