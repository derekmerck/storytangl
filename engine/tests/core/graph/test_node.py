import pytest
import uuid
import pickle

from tangl.core.graph import Node, Graph


# Test the Node class and its methods


def test_node_creation():
    n = Node(label="root")
    assert isinstance(n.uid, uuid.UUID)  # Ensure it's a UUID
    assert n.label == "root"
    assert n.parent is None

def test_add_child():
    g = Graph()
    parent = Node(label="parent")
    child = Node(label="child")

    g.add(parent)
    parent.add_child(child)

    assert child in parent.children
    assert child.parent == parent

    assert parent.child is child

    with pytest.raises(AttributeError):
        parent.does_not_exist

def test_remove_child():
    g = Graph()
    parent = Node(label="parent")
    child = Node(label="child")

    g.add(parent)
    parent.add_child(child)
    parent.remove_child(child)

    assert child not in parent.children
    assert child.parent is None

def test_unlink_child():
    g = Graph()
    parent = Node(label="parent")
    child = Node(label="child")
    grandchild1 = Node(label="grandchild1")
    grandchild2 = Node(label="grandchild2")

    g.add(parent)
    parent.add_child(child)
    child.add_child(grandchild1)
    child.add_child(grandchild2)

    assert child in parent.children
    assert child in g
    assert child.uid in g
    assert grandchild1 in child.children
    assert grandchild1 in g
    assert grandchild1.uid in g
    assert grandchild2 in child.children
    assert grandchild2 in g

    parent.remove_child(child, unlink=True) # removes tree
    assert child not in parent.children
    assert grandchild1 not in child.children
    assert grandchild2 not in child.children

    assert child not in g
    assert grandchild1 not in g
    assert grandchild2 not in g

def test_path():
    g = Graph()
    root = Node(label="root")
    child = Node(label="child")
    g.add(root)
    root.add_child(child)

    assert child.path == "root/child"

def test_root_property():
    g = Graph()
    root = Node(label="root")
    mid = Node(label="mid")
    leaf = Node(label="leaf")

    g.add(root)
    root.add_child(mid)
    mid.add_child(leaf)

    assert leaf.root == root

def test_cycle_detection():
    g = Graph()
    root = Node(label="root")
    child = Node(label="child")
    grandchild = Node(label="grandchild")

    g.add(root)
    root.add_child(child)
    child.add_child(grandchild)

    assert child.grandchild is grandchild

    with pytest.raises(ValueError, match="create a cycle"):
        grandchild.add_child(root)

def test_traversal_methods():
    g = Graph()
    root = Node(label="root")
    child1 = Node(label="child1")
    child2 = Node(label="child2")
    grandchild = Node(label="grandchild")

    g.add(root)
    root.add_child(child1)
    root.add_child(child2)
    child1.add_child(grandchild)

    # Test DFS
    dfs_order = [n.label for n in root.traverse_dfs()]
    assert dfs_order == ["root", "child1", "grandchild", "child2"]

    # Test BFS
    bfs_order = [n.label for n in root.traverse_bfs()]
    assert bfs_order == ["root", "child1", "child2", "grandchild"]

def test_visitor_pattern():
    g = Graph()
    root = Node(label="root")
    child = Node(label="child")
    g.add(root)
    root.add_child(child)

    visited = []

    def visitor(node: Node):
        visited.append(node.label)

    root.visit(visitor)
    assert visited == ["root", "child"]

def test_move_operations():
    g = Graph()
    root1 = Node(label="root1")
    root2 = Node(label="root2")
    child = Node(label="child")

    g.add(root1)
    g.add(root2)
    root1.add_child(child)

    assert child in root1.children

    # Test moving to new parent
    child.move_to(root2)
    assert child not in root1.children
    assert child in root2.children

    # Test moving to specific index
    child2 = Node(label="child2")
    root2.add_child(child2)
    child2.move_to(root2, 0)
    assert root2.children[0] == child2

def test_sibling_methods():
    g = Graph()
    root = Node(label="root")
    child1 = Node(label="child1")
    child2 = Node(label="child2")
    child3 = Node(label="child3")

    g.add(root)
    root.add_child(child1)
    root.add_child(child2)
    root.add_child(child3)

    assert set(c.uid for c in child1.siblings) == {child2.uid, child3.uid}
    assert child1 not in child1.siblings

def test_leaf_nodes():
    g = Graph()
    root = Node(label="root")
    child1 = Node(label="child1")
    child2 = Node(label="child2")
    grandchild = Node(label="grandchild")

    g.add(root)
    root.add_child(child1)
    root.add_child(child2)
    child1.add_child(grandchild)

    leaves = root.leaf_nodes
    assert len(leaves) == 2
    assert set(n.label for n in leaves) == {"grandchild", "child2"}




#  Tests that creating a new Node instance with default values sets guid, parent, children, metadata, content, and tags to their default values.
def test_create_node_with_default_values():
    node = Node()
    assert isinstance(node.uid, uuid.UUID)
    assert node.parent_id is None
    assert node.parent is None
    assert node.children_ids == []
    assert node.children == []

#  Tests that adding a child node to a parent node updates the child's parent and adds the child to the parent's children list.
def test_add_child_node():
    parent = Node()
    child = Node()
    parent.add_child(child)
    assert child.parent == parent
    assert child in parent.children

    assert child in parent.graph
    assert child.graph is parent.graph

def test_remove_child():
    parent = Node()
    child = Node()
    parent.add_child(child)

    assert child in parent.children
    assert child.parent_id == parent.uid

    parent.remove_child(child)
    assert child not in parent.children
    assert child.parent_id is None


def test_find_child():
    graph = Graph()
    parent = Node(graph=graph)
    child = Node(label="child")
    parent.add_child(child)

    found_child = parent.find_child(label = "child")
    assert found_child is not None
    assert found_child.label == "child"


def test_node_tags1():

    node = Node(tags=['dog', 'cat'])
    assert 'dog' in node.tags
    assert node.has_tags('dog')
    assert node.has_tags('dog', 'cat')
    assert not node.has_tags("bird")


def test_node_tags2():

    node = Node()
    node.tags.add("tag1")
    node.tags.add("tag2")
    assert node.has_tags("tag1", "tag2")
    assert not node.has_tags("tag1", "tag3")


def test_node_creation_and_default_label():
    node = Node()
    assert node.uid is not None
    assert node.label is not None
    assert node.short_uid.startswith(node.label), "label is the shortuuid encoded uid"


def test_node_creation_with_label():

    n = Node(label="foo")
    assert n.label == "foo"


def test_parent_child_relationship():
    parent = Node(label='parent')
    child = Node(label='child')

    graph = Graph()
    graph.add(parent)
    parent.add_child(child)

    assert child.parent == parent
    assert parent.children == [child]


#  Tests that retrieving the root node of a node returns the topmost parent node.
def test_get_root_node():
    grandparent = Node()
    parent = Node()
    child = Node()
    grandparent.add_child(parent)
    parent.add_child(child)
    assert child.root == grandparent


def test_node_path_names():
    graph = Graph()
    root = Node(label="root", graph=graph)
    child1 = Node(label="child1")
    root.add_child(child1)
    child2 = Node(label="child2")
    root.add_child(child2)
    grandchild1 = Node(label="grandchild1")
    child1.add_child(grandchild1)
    grandchild2 = Node(label="grandchild2")
    child1.add_child(grandchild2)
    assert root.path == "root"
    assert child1.path == "root/child1"
    assert child2.path == "root/child2"
    assert grandchild1.path == "root/child1/grandchild1"
    assert grandchild2.path == "root/child1/grandchild2"

    assert root in root.graph
    assert "root" in root.graph
    assert "root/child1" in root.graph
    assert "root/child1/grandchild2" in root.graph


#  Tests that retrieving the path of a node returns a string representing the node's position in the graph.
def test_node_path_construction1():
    grandparent = Node()
    parent = Node()
    child = Node()
    grandparent.add_child(parent)
    parent.add_child(child)
    assert child.path == f"{grandparent.label}/{parent.label}/{child.label}"


def test_node_path_construction2():
    root = Node(label='root')
    child = Node(label='child')
    grandchild = Node(label='grandchild')

    graph = Graph()
    graph.add(root)
    root.add_child(child)
    child.add_child(grandchild)

    child.parent_id = root.uid
    grandchild.parent_id = child.uid

    assert grandchild.path == 'root/child/grandchild'


def test_graph_node_retrieval():
    node = Node()
    graph = Graph()
    graph.add(node)

    retrieved_node = graph.get(node.uid)
    assert retrieved_node == node

    assert graph.get(uuid.uuid4()) is None, "Non-existent node returns None"

    node2 = Node(label="foo", data={'bar': 3})
    graph.add(node2)

    assert graph.get("foo") is node2

# Fixture to create a simple graph with nodes
@pytest.fixture
def simple_graph():
    graph = Graph()
    parent = Node(label="parent", graph=graph)
    child1 = Node(label="child1", graph=graph)
    child2 = Node(label="child2", graph=graph)
    child3 = Node(label="child3", graph=graph)

    parent.add_child(child1)
    parent.add_child(child2)
    child1.add_child(child3)

    # graph.add(parent)
    # graph.add(child1)
    # graph.add(child2)
    # graph.add(child3)

    return graph, parent, child1, child2, child3

def test_node_root(simple_graph):
    _, parent, child1, _, child3 = simple_graph

    # Root of the parent should be the parent itself
    assert parent.root == parent

    # Root of any child should be the parent
    assert child1.root == parent
    assert child3.root == parent

def test_node_find_children(simple_graph):
    _, parent, child1, _, _ = simple_graph

    # Find all children of the parent node
    assert len(parent.children) == 2
    assert child1 in parent.children

def test_node_find_child(simple_graph):
    _, parent, child1, child2, _ = simple_graph

    # Find a single child of the parent node
    found_child = parent.find_child(label="child2")
    assert found_child is child2
    # assert found_child in [ child1, child2 ]

@pytest.mark.xfail(reason="no setter", raises=AttributeError)
def test_node_parent_setter(simple_graph):
    _, parent, child1, child2, child3 = simple_graph

    # Change the parent of child3 to child2
    child3.parent = child2
    assert child3.parent == child2

    # Test that child3 is no longer a child of child1
    assert child3 not in child1.children

    # Test that child3 is now a child of child2
    assert child3 in child2.children

    # Test setting parent to None
    child3.parent = None
    assert child3.parent is None
    assert child3 not in child2.children

    # Test setting parent using Uid
    child3.parent = child1.uid
    assert child3.parent == child1
    assert child3 in child1.children

    # Test raising TypeError for invalid type
    with pytest.raises(TypeError):
        child3.parent = 123  # Invalid type for parent


def test_caching_behavior():
    registry = Graph()

    # Add some nodes
    node1 = Node()
    registry.add(node1)
    node2 = Node()
    registry.add(node2)

    # Check cache behavior
    nodes_by_path1 = registry.nodes_by_path
    nodes_by_path2 = registry.nodes_by_path
    assert nodes_by_path1 is nodes_by_path2  # Should be the same object (cached)

    # Invalidate cache by adding a new node
    node3 = Node()
    registry.add(node3)
    nodes_by_path3 = registry.nodes_by_path
    assert nodes_by_path3 is not nodes_by_path2  # Should be a different object (cache invalidated)


def test_node_pickles():

    a = Node(label="test_node")

    s = pickle.dumps( a )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert a == res
