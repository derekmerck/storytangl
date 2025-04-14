from tangl.core.graph import Graph, Node, Edge


def test_edge_creation():
    g = Graph()
    n1 = Node(label="A")
    n2 = Node(label="B")
    g.add(n1)
    g.add(n2)

    e = Edge(label="edge", predecessor_id=n1.uid, successor_id=n2.uid)
    g.add(e)

    assert e.predecessor == n1
    assert e.successor == n2

    n1.add_child(e)
    assert e.label == "edge"
    assert n1.edge is n2

def test_edge_creation2():
    # alternate, simpler argument format for node creation
    g = Graph()
    n1 = Node(label="A", graph=g)
    n2 = Node(label="B", graph=g)

    e = Edge(label="edge", predecessor_id=n1.uid, successor_id=n2.uid, graph=g)

    assert e.predecessor == n1
    assert e.successor == n2

    assert e.label == "edge"
    assert n1.edge is n2

