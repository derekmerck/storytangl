import pytest
from uuid import uuid4

from tangl.core.graph import Node, Edge, Graph

class TestNode:

    def test_node_creation(self):
        n = Node(label="root")
        assert isinstance(n.uid, uuid4().__class__)  # Ensure it's a UUID
        assert n.label == "root"
        assert n.parent is None

    def test_add_child(self):
        g = Graph()
        parent = Node(label="parent")
        child = Node(label="child")

        g.add(parent)
        parent.add_child(child)

        assert child in parent.children
        assert child.parent == parent

    def test_remove_child(self):
        g = Graph()
        parent = Node(label="parent")
        child = Node(label="child")

        g.add(parent)
        parent.add_child(child)
        parent.remove_child(child)

        assert child not in parent.children
        assert child.parent is None

    def test_unlink_child(self):
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
        assert child.uid in g
        assert grandchild1 in child.children
        assert grandchild1.uid in g
        assert grandchild2 in child.children
        assert grandchild2.uid in g

        parent.remove_child(child, unlink=True) # removes tree
        assert child not in parent.children
        assert grandchild1 not in child.children
        assert grandchild2 not in child.children

        assert child.uid not in g
        assert grandchild1.uid not in g
        assert grandchild2.uid not in g

    def test_path(self):
        g = Graph()
        root = Node(label="root")
        child = Node(label="child")
        g.add(root)
        root.add_child(child)

        assert child.path == "root/child"

    def test_root_property(self):
        g = Graph()
        root = Node(label="root")
        mid = Node(label="mid")
        leaf = Node(label="leaf")

        g.add(root)
        root.add_child(mid)
        mid.add_child(leaf)

        assert leaf.root == root

    def test_cycle_detection(self):
        g = Graph()
        root = Node(label="root")
        child = Node(label="child")
        grandchild = Node(label="grandchild")

        g.add(root)
        root.add_child(child)
        child.add_child(grandchild)

        with pytest.raises(ValueError, match="create a cycle"):
            grandchild.add_child(root)

    def test_traversal_methods(self):
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

    def test_visitor_pattern(self):
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

    def test_move_operations(self):
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

    def test_sibling_methods(self):
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

    def test_leaf_nodes(self):
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

class TestEdge:

    def test_edge_creation(self):
        g = Graph()
        n1 = Node(label="A")
        n2 = Node(label="B")
        g.add(n1)
        g.add(n2)

        e = Edge(predecessor_id=n1.uid, successor_id=n2.uid)
        g.add(e)

        assert e.predecessor == n1
        assert e.successor == n2

class TestGraph:

    def test_graph_add_and_retrieve(self):
        g = Graph()
        n = Node(label="root")
        g.add(n)

        assert g[n.uid] == n
        assert g["root"] == n

    def test_graph_prevents_duplicates(self):
        g = Graph()
        n = Node(label="root")
        g.add(n)
        assert n.graph == g

        n.graph = None
        with pytest.raises(ValueError):
            g.add(n)  # Should raise because already in graph but graph is not set properly

    def test_graph_lookup_by_label(self):
        g = Graph()
        n1 = Node(label="root")
        n2 = Node(label="child")

        g.add(n1)
        n1.add_child(n2)

        assert g["root/child"] == n2

    def test_graph_missing_node_raises_key_err(self):
        g = Graph()

        with pytest.raises(KeyError):
            assert g["nonexistent"] is None

    def test_graph_unstructure_structure(self):
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
