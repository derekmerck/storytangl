import pytest
from uuid import uuid4
import pickle

from tangl.core.graph import Node, Graph


def test_graph_add_and_retrieve():
    g = Graph()
    n = Node(label="root")
    g.add(n)

    assert g.get(n.uid) == n
    assert g.find_one(label="root") == n


def test_graph_contains():
    g = Graph()
    n = Node(label="root", graph=g)

    assert n in g
    assert n.uid in g

@pytest.mark.skip(reason="deprecated behavior")
def test_graph_prevents_duplicates():
    g = Graph()
    n = Node(label="root")
    g.add(n)
    assert n.graph == g

    n.graph = None
    with pytest.raises(ValueError):
        g.add(n)  # Should raise because already in graph but graph is not set properly

@pytest.mark.skip(reason="deprecated behavior")
def test_graph_missing_node_raises_key_err():
    g = Graph()

    with pytest.raises(KeyError):
        assert g.get("nonexistent") is None

def test_graph_unstructure_structure():
    g = Graph()
    root = Node(label="root", graph=g)
    mid = Node(label="mid", graph=g)
    leaf = Node(label="leaf", graph=g)

    root.add_edge_to(mid)
    mid.add_edge_to(leaf)

    # assert leaf.root == root

    structured = g.unstructure()
    restored = Graph.structure(structured)

    restored_leaf = restored.get(leaf.uid)
    assert restored_leaf == leaf
    restored_root = restored.get(root.uid)
    # assert restored_leaf.root == restored_root

def test_add_node():
    graph = Graph()
    node = Node()
    graph.add(node)

    assert node in graph

def test_get_node_by_uuid():
    graph = Graph()
    node = Node()
    graph.add(node)

    retrieved_node = graph.get(node.uid)
    assert retrieved_node is node

def test_get_node_by_label():
    graph = Graph()
    node = Node(label="unique_label")
    graph.add(node)

    retrieved_node = graph.find_one(label="unique_label")
    assert retrieved_node == node

class TestNodeByCls(Node):
    ...

# todo: revisit find by tags
@pytest.mark.xfail(reason="find by tags not working correctly yet, need to revisit tags")
def test_find_nodes():
    registry = Graph()

    # Create some nodes with specific tags
    node1 = Node(tags=['red'])
    node2 = Node(tags=['blue'])
    node3 = TestNodeByCls(tags=['red', 'blue'])
    registry.add(node1)
    registry.add(node2)
    registry.add(node3)

    assert registry.all() == [node1, node2, node3]

    # Test finding nodes by type
    assert list(registry.find_all(has_cls=TestNodeByCls)) == [node3]

    # Test finding nodes by filter
    assert list(registry.find_all(tags={"red"})) == [node1, node3]

    # Test finding nodes by tags
    assert list(registry.find_all(tags=node1.tags)) == [node1, node3]



def test_graph_pickles():

    graph = Graph()
    node = Node(label="node", graph=graph)
    child = Node(label="child", graph=graph)
    node.add_edge_to(child)

    # assert child.parent is node
    assert child.graph is node.graph
    assert node.uid in node.graph
    assert child.uid in node.graph

    s = pickle.dumps( graph )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert graph == res
