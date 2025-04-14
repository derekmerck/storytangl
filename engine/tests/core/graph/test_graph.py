import pytest
from uuid import uuid4
import pickle

from tangl.core import Node, Graph


def test_graph_add_and_retrieve():
    g = Graph()
    n = Node(label="root")
    g.add(n)

    assert g[n.uid] == n
    assert g["root"] == n

def test_graph_prevents_duplicates():
    g = Graph()
    n = Node(label="root")
    g.add(n)
    assert n.graph == g

    n.graph = None
    with pytest.raises(ValueError):
        g.add(n)  # Should raise because already in graph but graph is not set properly

def test_graph_lookup_by_label():
    g = Graph()
    n1 = Node(label="root")
    n2 = Node(label="child")

    g.add(n1)
    n1.add_child(n2)

    assert g["root/child"] == n2

def test_graph_missing_node_raises_key_err():
    g = Graph()

    with pytest.raises(KeyError):
        assert g["nonexistent"] is None

def test_graph_unstructure_structure():
    g = Graph()
    root = Node(label="root")
    mid = Node(label="mid")
    leaf = Node(label="leaf")

    g.add(root)
    root.add_child(mid)
    mid.add_child(leaf)

    assert leaf.root == root

    structured = g.unstructure()
    restored = Graph.structure(structured)

    restored_leaf = restored[leaf.uid]
    assert restored_leaf == leaf
    restored_root = restored[root.uid]
    assert restored_leaf.root == restored_root

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

    retrieved_node = graph.get("unique_label")
    assert retrieved_node == node

class TestNodeByCls(Node):
    ...

def test_find_nodes():
    registry = Graph()

    # Create some nodes with specific tags
    node1 = Node(tags=['red'])
    node2 = Node(tags=['blue'])
    node3 = TestNodeByCls(tags=['red', 'blue'])
    registry.add(node1)
    registry.add(node2)
    registry.add(node3)

    assert list(registry.values()) == [node1, node2, node3]

    # Test finding nodes by type
    assert registry.find(has_cls=TestNodeByCls) == [node3]

    # Test finding nodes by filter
    assert registry.find(tags="red") == [node1, node3]

    # Test finding nodes by tags
    assert registry.find(tags=node1.tags) == [node1, node3]

def test_node_and_registry():
    index = Graph()
    print( index.nodes_by_path )

    root = Node(label='root', graph=index)

    assert root.graph is index
    assert root in index

    child1 = Node(label='child1')
    root.add_child(child1)
    assert child1 in root.children

    assert child1.graph is index

    print(index.keys())

    assert child1 in index
    assert child1.path in index
    assert child1.uid in index

    child2 = Node(label='child2')
    root.add_child(child2)
    assert child2 in root.children
    # index.add_node(child2)
    #
    assert len(root.children) == 2
    assert index.get(root.uid) == root
    assert index.get(root.uid) == root
    assert index.get(child1.uid) == child1
    assert index.get(child2.uid) == child2
    assert index.get(root.path) == root
    assert index.get(root.path) == root
    assert index.get(child1.path) == child1
    assert index.get(child2.path) == child2

    assert root.graph == index
    assert child1.graph == index
    assert child2.graph == index

    assert child1 in root.children
    root.remove_child(child1)
    assert child1 not in root.children

    print( child2.parent )
    print( root.children_ids )
    assert child2.uid in root.children_ids

    index.remove(child2)
    assert child2 not in index

    assert index.get("dog") is None

    assert index.get(uuid4()) is None

    assert index.get(100) is None

    assert 100 not in index

def test_complex_hierarchies():
    root = Node(label="r")
    registry = Graph()
    registry.add(root)

    # Create child nodes
    child1 = Node(label="ch1")
    child2 = Node(label="ch2")
    root.add_child(child1)
    root.add_child(child2)

    # Create grandchild nodes
    grandchild1 = Node(label="gch1")
    grandchild2 = Node(label="gch2")
    child1.add_child(grandchild1)
    child2.add_child(grandchild2)

    # Check hierarchy and paths
    assert root.path == root.label
    assert child1.path == f"{root.label}/{child1.label}"
    assert grandchild1.path == f"{root.label}/{child1.label}/{grandchild1.label}"

    print( registry.keys() )
    print( registry.nodes_by_path.keys() )

    # Check registry nodes by path
    assert registry.nodes_by_path == {
        root.path: root,
        child1.path: child1,
        child2.path: child2,
        grandchild1.path: grandchild1,
        grandchild2.path: grandchild2,
    }

def test_graph_pickles():

    graph = Graph()
    node = Node(label="node", graph=graph)
    child = Node(label="child")
    node.add_child(child)

    assert child.parent is node
    assert child.graph is node.graph
    assert node.uid in node.graph
    assert child.uid in node.graph

    s = pickle.dumps( graph )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert graph == res
