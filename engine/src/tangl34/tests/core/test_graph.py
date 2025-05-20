import pytest
from tangl34.core.structure.node import Node
from tangl34.core.structure.edge import Edge, EdgeKind
from tangl34.core.structure.graph import Graph

def make_graph():
    g = Graph()
    n1 = Node(label="start")
    n2 = Node(label="end")
    g.add(n1)
    g.add(n2)
    e = Edge(src_id=n1.uid, dst_id=n2.uid, edge_kind=EdgeKind.CHOICE)
    g.add(e)
    return g, n1, n2, e

def test_graph_node_edge_add_get():
    g, n1, n2, e = make_graph()
    assert g.get(n1.uid) is n1
    assert g.get(n2.uid) is n2
    assert g.get(e.uid) is e

def test_find_edges_direction_and_kind():
    g, n1, n2, e = make_graph()
    # Outgoing from n1
    outs = list(g.find_edges(n1, direction="out"))
    assert outs == [e]
    # Incoming to n2
    ins = list(g.find_edges(n2, direction="in"))
    assert ins == [e]
    # Filter by kind
    choices = list(g.find_edges(n1, direction="out", edge_kind=EdgeKind.CHOICE))
    assert choices == [e]

def test_node_edges_delegates_to_graph():
    g, n1, n2, e = make_graph()
    edges = list(n1.edges(g, direction="out", edge_kind=EdgeKind.CHOICE))
    assert edges == [e]