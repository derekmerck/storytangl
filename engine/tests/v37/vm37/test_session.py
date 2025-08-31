from tangl.core.graph import Node, Graph
from tangl.vm.session import ResolutionPhase as P, Session

def test_ns_contract(session):
    ns = session.run_phase(P.VALIDATE)
    assert "cursor" in ns and "phase" in ns and "results" in ns

def test_follow_edge_stops_without_next(session):
    g = session.graph
    n = Node(label="def")
    g.add(n)
    assert n in g
    assert session.cursor.label == "abc"
    assert session.context.cursor.label == "abc"
    e = g.add_edge(session.cursor, n)
    assert e in g
    assert session.follow_edge(e) is None
    assert session.cursor_id == n.uid
    assert session.cursor is n, f'cursor should be {n!r}, not {session.cursor!r}'
    assert session.context.cursor is n


def test_session_follow_edge_updates_cursor_and_stops():
    g = Graph()
    n1 = g.add_node(label="A")
    n2 = g.add_node(label="B")
    e  = g.add_edge(n1, n2)
    sess = Session(graph=g, cursor_id=n1.uid, event_sourced=False)

    out = sess.follow_edge(e)
    assert out is None
    assert sess.cursor.uid == n2.uid

def test_session_context_ns_has_phase_and_results():
    g = Graph()
    n = g.add_node(label="A")
    sess = Session(graph=g, cursor_id=n.uid)
    ns = sess.get_ns(P.VALIDATE)
    assert ns["phase"] is P.VALIDATE
    assert isinstance(ns["results"], list)
