from uuid import uuid4
from tangl.core.entity import Graph, Node


def test_graph_lookup_by_path():
    g = Graph()
    n1 = Node(label="root")
    n2 = Node(label="child")

    g.add(n1)
    n1.add_edge(n2)

    assert g.find_one(path="root/child") == n2

def test_node_ancestors_path():
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
    root.add_edge(child1)
    root.add_edge(child2)

    # Create grandchild nodes
    grandchild1 = Node(label="gch1")
    grandchild2 = Node(label="gch2")
    child1.add_edge(grandchild1)
    child2.add_edge(grandchild2)

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
