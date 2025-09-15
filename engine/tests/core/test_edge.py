from tangl.core.graph import Graph, Node, Edge


def test_edge_creation():
    g = Graph()
    n1 = Node(label="A")
    n2 = Node(label="B")
    g.add(n1)
    g.add(n2)

    e = Edge(label="edge", source_id=n1.uid, destination_id=n2.uid)
    g.add(e)

    assert e.source == n1
    assert e.destination == n2
    assert e.label == "edge"

    # n1.add_child(e)
    # assert n1.edge is n2

def test_edge_creation2():
    # alternate, simpler argument format for node creation
    g = Graph()
    n1 = Node(label="A", graph=g)
    n2 = Node(label="B", graph=g)

    e = g.add_edge(n1, n2, label="edge")

    assert e.source == n1
    assert e.destination == n2
    assert e.label == "edge"
    # assert n1.edge is n2

