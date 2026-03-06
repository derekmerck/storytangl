"""Tests for tangl.core.graph (Graph, Node, Edge, Subgraph)

Organized by functionality:
- Graph basics: creation, add, get, contains
- Node and Edge operations
- Subgraph membership and hierarchy
- Parent chains, ancestors, and paths
- Edge queries and helpers
- Serialization: unstructure/structure/pickle
- Graph equality and data
"""
from __future__ import annotations

import pickle
import pytest
from uuid import UUID, uuid4

from tangl.core import Entity
from tangl.core.graph import Graph, GraphItem, Node, Edge, Subgraph


# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================

class SubclassNode(Node):
    """Test node subclass for testing type filtering."""
    pass


def make_simple_graph():
    """Helper to create a simple graph with two nodes and an edge."""
    g = Graph()
    n1 = Node(label="start")
    n2 = Node(label="end")
    g.add(n1)
    g.add(n2)
    e = Edge(source_id=n1.uid, destination_id=n2.uid)
    g.add(e)
    return g, n1, n2, e


def _uuids_unique(items):
    """Helper to verify all items have unique UUIDs."""
    seen = set()
    for it in items:
        assert isinstance(it.uid, UUID)
        assert it.uid not in seen
        seen.add(it.uid)


# ============================================================================
# Graph Basics
# ============================================================================

class TestGraphBasics:
    """Tests for basic graph creation and operations."""

    def test_graph_creation(self):
        """Test creating an empty graph."""
        g = Graph()
        assert isinstance(g, Graph)
        assert len(list(g.values())) == 0

    def test_graph_with_label(self):
        """Test creating a labeled graph."""
        g = Graph(label="MyGraph")
        assert g.label == "MyGraph"

    def test_add_node_to_graph(self):
        """Test adding a node to a graph."""
        g = Graph()
        n = Node(label="root")
        g.add(n)
        assert n in g
        assert n.graph == g

    def test_add_node_via_add_node_helper(self):
        """Test using Graph.add_node() helper."""
        g = Graph()
        n = g.add_node(label="test")
        assert isinstance(n, Node)
        assert n.label == "test"
        assert n in g

    def test_get_node_by_uuid(self):
        """Test retrieving node by UUID."""
        g = Graph()
        n = Node(label="root")
        g.add(n)
        retrieved = g.get(n.uid)
        assert retrieved is n

    def test_get_node_by_label(self):
        """Test retrieving node by label using find_one."""
        g = Graph()
        n = Node(label="unique_label")
        g.add(n)
        retrieved = g.find_one(label="unique_label")
        assert retrieved == n

    def test_get_returns_none_for_missing_uuid(self):
        """Test that get() returns None for non-existent UUID."""
        g = Graph()
        assert g.get(UUID(int=0)) is None

    def test_graph_contains_node(self):
        """Test 'in' operator for graphs."""
        g = Graph()
        n = Node(label="root", graph=g)
        assert n in g
        assert n.uid in g

    def test_graph_prevents_duplicate_uids(self):
        """Test that adding item with duplicate UID raises error."""
        g = Graph()
        n = Node(label="root")
        g.add(n)

        # Adding same node again should be idempotent if graph is set correctly
        n.graph = None
        g.add(n)  # Should NOT raise

        # But adding different node with same UID should raise
        imposter = Node(uid=n.uid, label="imposter")
        with pytest.raises(ValueError):
            g.add(imposter)

    def test_graph_values(self):
        """Test iterating over graph values."""
        g = Graph()
        n1 = g.add_node(label="a")
        n2 = g.add_node(label="b")
        values = list(g.values())
        assert n1 in values
        assert n2 in values

    def test_duplicate_labels_allowed(self):
        """Test that duplicate labels are allowed but UUID lookup is unambiguous."""
        g = Graph()
        a = g.add_node(label="X")
        b = g.add_node(label="X")
        # Label lookup may return either
        assert g.get("X") in (a, b)
        # UUID lookup is unambiguous
        assert g.get(a.uid) is a
        assert g.get(b.uid) is b


# ============================================================================
# Node and Edge Operations
# ============================================================================

class TestNodeAndEdgeOperations:
    """Tests for node and edge creation and manipulation."""

    def test_add_edge_between_nodes(self):
        """Test creating an edge between two nodes."""
        g = Graph()
        n1 = g.add_node(label="a")
        n2 = g.add_node(label="b")
        e = g.add_edge(n1, n2, label="ab")

        assert isinstance(e, Edge)
        assert e.source_id == n1.uid
        assert e.destination_id == n2.uid
        assert e in g

    def test_edge_source_destination_properties(self):
        """Test edge source and destination property accessors."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        e = g.add_edge(a, b, label="ab")

        # Properties resolve through the graph
        assert e.source is a
        assert e.destination is b

    def test_edge_reassign_destination(self):
        """Test reassigning edge destination via property."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        c = g.add_node(label="c")
        e = g.add_edge(a, b, label="ab")

        # Reassign destination
        e.destination = c
        assert e.destination_id == c.uid
        assert e.destination is c

    def test_edge_clear_source(self):
        """Test clearing edge source."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        e = g.add_edge(a, b)

        e.source = None
        assert e.source_id is None
        assert e.source is None

    def test_edge_type_safety(self):
        """Test that edge endpoints must be nodes."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        e = g.add_edge(a, b)

        with pytest.raises(TypeError):
            e.source = "not-a-node"  # type: ignore[assignment]

    def test_node_add_edge_to(self):
        """Test Node.add_edge_to() convenience method."""
        g = Graph()
        root = Node(label="root", graph=g)
        mid = Node(label="mid", graph=g)
        leaf = Node(label="leaf", graph=g)

        root.add_edge_to(mid)
        mid.add_edge_to(leaf)

        # Edges should exist in graph
        assert len(list(g.find_edges())) == 2

    def test_find_edges_by_direction(self):
        """Test finding edges by source and destination."""
        g, n1, n2, e = make_simple_graph()

        # Outgoing from n1
        outs = list(g.find_edges(source=n1))
        assert outs == [e]

        # Incoming to n2
        ins = list(g.find_edges(destination=n2))
        assert ins == [e]

    def test_node_edges_out_helper(self):
        """Test Node.edges_out() helper method."""
        g, n1, n2, e = make_simple_graph()
        edges = list(n1.edges_out())
        assert edges == [e]

    def test_node_edges_in_helper(self):
        """Test Node.edges_in() helper method."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        e = g.add_edge(n1, n2)

        assert list(n1.edges_out()) == [e]
        assert list(n2.edges_in()) == [e]

    def test_node_edges_helper(self):
        """Test Node.edges() returns all connected edges."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        e = g.add_edge(n1, n2, label="e")

        assert n1.edges() == [e]
        assert n2.edges() == [e]


# ============================================================================
# Subgraph and Hierarchy
# ============================================================================

class TestSubgraphOperations:
    """Tests for subgraph creation and membership."""

    def test_create_subgraph(self):
        """Test creating a subgraph."""
        g = Graph()
        sg = g.add_subgraph(label="S")
        assert isinstance(sg, Subgraph)
        assert sg in g

    def test_subgraph_with_members(self):
        """Test creating subgraph with initial members."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        sg = g.add_subgraph(label="S", members=[n1, n2])

        assert sg.has_member(n1)
        assert sg.has_member(n2)
        assert list(sg.members) == [n1, n2]

    def test_subgraph_add_member(self):
        """Test adding members to subgraph."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        c = g.add_node(label="c")

        sg = g.add_subgraph(label="S", members=[a])
        sg.add_member(b)

        assert sg.has_member(a)
        assert sg.has_member(b)
        assert not sg.has_member(c)

    def test_subgraph_remove_member(self):
        """Test removing members from subgraph."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        sg = g.add_subgraph(label="S", members=[a, b])

        sg.remove_member(a)
        assert not sg.has_member(a)
        assert sg.has_member(b)

    def test_subgraph_remove_member_by_uuid(self):
        """Test removing member by UUID."""
        g = Graph()
        n = g.add_node(label="X")
        sg = g.add_subgraph(label="G", members=[n])

        sg.remove_member(n.uid)
        assert n.uid not in sg.member_ids

    def test_subgraph_find_members(self):
        """Test finding members in subgraph."""
        g = Graph()
        a = g.add_node(label="a")
        b = g.add_node(label="b")
        sg = g.add_subgraph(label="S", members=[a, b])

        got = list(sg.find_all(label="b"))
        assert got == [b]
        assert sg.find_one(label="b") is b
        assert sg.find_one(label="z") is None

    def test_subgraph_type_safety_add(self):
        """Test that subgraph.add_member enforces type."""
        g = Graph()
        sg = g.add_subgraph(label="S")

        with pytest.raises(TypeError):
            sg.add_member("not-a-node")  # type: ignore[arg-type]

    def test_subgraph_type_safety_remove(self):
        """Test that subgraph.remove_member enforces type."""
        g = Graph()
        sg = g.add_subgraph(label="S")

        with pytest.raises(TypeError):
            sg.remove_member("not-a-node")  # type: ignore[arg-type]

    def test_nested_subgraphs(self):
        """Test nesting subgraphs within subgraphs."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        top = g.add_subgraph(label="Top")
        mid = g.add_subgraph(label="Mid")

        top.add_member(a)
        mid.add_member(b)
        top.add_member(mid)  # Nest subgraph

        # Parent chain: b -> mid -> top
        assert b.parent == mid
        assert list(b.ancestors()) == [mid, top]


# ============================================================================
# Parent Chains, Ancestors, and Paths
# ============================================================================

class TestGraphHierarchy:
    """Tests for parent chains, ancestors, root, and paths."""

    def test_node_parent(self):
        """Test node parent relationship."""
        g = Graph()
        n = g.add_node(label="n")
        sg = g.add_subgraph(label="S", members=[n])

        assert n.parent is sg

    def test_node_parent_none_when_not_member(self):
        """Test that parent is None when node not in subgraph."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        sg = g.add_subgraph(label="S", members=[n1])

        assert n1.parent is sg
        assert n2.parent is None

    def test_node_ancestors(self):
        """Test node.ancestors() returns parent chain."""
        g = Graph()
        n = g.add_node(label="n")
        sg = g.add_subgraph(label="A", members=[n])

        assert list(n.ancestors()) == [sg]

    def test_node_ancestors_nested(self):
        """Test ancestors with nested subgraphs."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        top = g.add_subgraph(label="Top")
        mid = g.add_subgraph(label="Mid")

        top.add_member(a)
        mid.add_member(b)
        top.add_member(mid)

        # Ancestors are nearest -> farthest
        assert list(b.ancestors()) == [mid, top]

    def test_node_root(self):
        """Test node.root returns farthest ancestor."""
        g = Graph()
        n = g.add_node(label="n")
        sg = g.add_subgraph(label="A", members=[n])

        assert n.root is sg

    def test_node_root_nested(self):
        """Test root with nested hierarchy."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        top = g.add_subgraph(label="Top")
        mid = g.add_subgraph(label="Mid")

        top.add_member(a)
        mid.add_member(b)
        top.add_member(mid)

        assert b.root == top

    def test_node_path(self):
        """Test node.path shows hierarchy."""
        g = Graph()
        n = g.add_node(label="n")
        sg = g.add_subgraph(label="A", members=[n])

        assert n.path == "A.n"

    def test_node_path_nested(self):
        """Test path with nested subgraphs."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        top = g.add_subgraph(label="Top")
        mid = g.add_subgraph(label="Mid")

        top.add_member(a)
        mid.add_member(b)
        top.add_member(mid)

        assert b.path == "Top.Mid.B"

    def test_path_with_simple_hierarchy(self):
        """Test path generation."""
        g = Graph()
        n1 = g.add_node(label="root")
        n2 = g.add_node(label="scene")
        sg = g.add_subgraph(label="book", members=[n1, n2])

        assert n2.parent == sg
        assert list(n2.ancestors()) == [sg]
        assert n2.path.endswith(".scene") or n2.path == "book.scene"

    def test_subgraph_reparenting(self):
        """Test that adding member to new subgraph updates parent."""
        g = Graph()
        a = g.add_node(label="A")
        s1 = g.add_subgraph(label="S1", members=[a])

        assert a.parent is s1

        s2 = g.add_subgraph(label="S2")
        s2.add_member(a)

        assert a.parent is s2
        assert list(a.ancestors())[0] == s2
        assert s1 is not a.parent


# ============================================================================
# Find Operations
# ============================================================================

class TestGraphFindOperations:
    """Tests for finding nodes, edges, and subgraphs."""

    def test_find_nodes(self):
        """Test finding all nodes."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")

        nodes = {x.label for x in g.find_nodes()}
        assert nodes == {"n1", "n2"}

    def test_find_edges(self):
        """Test finding all edges."""
        g = Graph()
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        e = g.add_edge(n1, n2, label="e1")

        edges = {x.label for x in g.find_edges()}
        assert edges == {"e1"}

    def test_find_subgraphs(self):
        """Test finding all subgraphs."""
        g = Graph()
        sg = g.add_subgraph(label="sg1")

        subgraphs = {x.label for x in g.find_subgraphs()}
        assert subgraphs == {"sg1"}

    def test_find_nodes_by_type(self):
        """Test finding nodes by class type."""
        g = Graph()
        node1 = Node(tags=['red'])
        node2 = Node(tags=['blue'])
        node3 = SubclassNode(tags=['red', 'blue'])
        g.add(node1)
        g.add(node2)
        g.add(node3)

        # Find by type
        assert list(g.find_all(is_instance=SubclassNode)) == [node3]

    def test_find_nodes_by_tags(self):
        """Test finding nodes by tags."""
        g = Graph()
        node1 = Node(tags=['red'])
        node2 = Node(tags=['blue'])
        node3 = SubclassNode(tags=['red', 'blue'])
        g.add(node1)
        g.add(node2)
        g.add(node3)

        # Find by tags
        assert list(g.find_all(has_tags={"red"})) == [node1, node3]
        assert list(g.find_all(has_tags=node1.tags)) == [node1, node3]

    def test_comprehensive_find_operations(self):
        """Test comprehensive node/edge/subgraph finding."""
        g = Graph(label="G")

        # Create nodes
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        _uuids_unique([n1, n2])

        # Create edge
        e = g.add_edge(n1, n2, edge_type=None, label="e1")
        assert isinstance(e, Edge)
        assert e.source_id == n1.uid
        assert e.destination_id == n2.uid

        # Create subgraph
        sg = g.add_subgraph(label="sg1", members=[n1, n2])
        assert isinstance(sg, Subgraph)
        assert sg.has_member(n1) and sg.has_member(n2)
        assert list(sg.members) == [n1, n2]

        # Find operations
        assert {x.label for x in g.find_nodes()} == {"n1", "n2"}
        assert {x.label for x in g.find_subgraphs()} == {"sg1"}
        assert {x.label for x in g.find_edges()} == {"e1"}

        # Directional edge queries
        out_from_n1 = list(g.find_edges(source=n1))
        into_n2 = list(g.find_edges(destination=n2))
        assert out_from_n1 == [e]
        assert into_n2 == [e]

        # Get by UUID and label
        assert g.get(n1.uid) is n1
        assert g.get("n2") is n2
        assert g.get(UUID(int=0)) is None


# ============================================================================
# Serialization
# ============================================================================

class TestGraphSerialization:
    """Tests for graph serialization and deserialization."""

    def test_graph_unstructure(self):
        """Test graph unstructure to dict."""
        g = Graph(label="G")
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")

        blob = g.unstructure()
        assert isinstance(blob, dict)
        assert "_data" in blob
        assert isinstance(blob["_data"], list)

    def test_graph_structure(self):
        """Test graph structure from dict."""
        g = Graph()
        n = Node(label="root")
        g.add(n)

        structured = g.unstructure()
        restored = Graph.structure(structured)

        assert restored.get(n.uid) == n

    def test_graph_roundtrip_relinks_items(self):
        """Test that unstructure/structure relinks graph items."""
        g = Graph(label="G")
        n1 = GraphItem(label="n1")
        n2 = GraphItem(label="n2")
        g.add(n1)
        g.add(n2)

        # Items linked before serialization
        assert n1.graph is g and n2.graph is g

        blob = g.unstructure()

        # Graph backlink not serialized
        for item_blob in blob["_data"]:
            assert "graph" not in item_blob

        # Rebuild
        g2 = Graph.structure(dict(blob))

        # Items relinked to new graph
        rebuilt_items = list(g2.values())
        assert len(rebuilt_items) == 2
        for item in rebuilt_items:
            assert isinstance(item, GraphItem)
            assert item.graph is g2

    def test_graph_unstructure_structure_preserves_edges(self):
        """Test that edge endpoints are preserved through serialization."""
        g = Graph()
        root = Node(label="root", graph=g)
        mid = Node(label="mid", graph=g)
        leaf = Node(label="leaf", graph=g)

        root.add_edge_to(mid)
        mid.add_edge_to(leaf)

        structured = g.unstructure()
        restored = Graph.structure(structured)

        restored_leaf = restored.get(leaf.uid)
        assert restored_leaf == leaf

    def test_graph_roundtrip_preserves_subgraph_members(self):
        """Test that subgraph members are preserved."""
        g = Graph(label="G")
        n1 = g.add_node(label="n1")
        n2 = g.add_node(label="n2")
        e = g.add_edge(n1, n2, label="e1")
        sg = g.add_subgraph(label="S", members=[n1, n2])

        # Pre-conditions
        assert e.source is n1 and e.destination is n2
        assert list(sg.members) == [n1, n2]

        blob = g.unstructure()

        # Graph backlink not serialized
        for item_blob in blob["_data"]:
            assert "graph" not in item_blob

        # Rebuild
        g2 = Graph.structure(dict(blob))

        # Find items
        nodes2 = {x.label: x for x in g2.find_nodes()}
        edges2 = {x.label: x for x in g2.find_edges()}
        sg2 = next(g2.find_subgraphs())

        assert set(nodes2.keys()) == {"n1", "n2"}
        assert set(edges2.keys()) == {"e1"}

        # Edge endpoints resolve correctly
        e2 = edges2["e1"]
        assert isinstance(e2, Edge)
        assert e2.source.label == "n1"
        assert e2.destination.label == "n2"

        # Subgraph members preserved
        assert [m.label for m in sg2.members] == ["n1", "n2"]

    def test_graph_pickle_roundtrip(self):
        """Test pickling and unpickling graph."""
        graph = Graph()
        node = Node(label="node", graph=graph)
        child = Node(label="child", graph=graph)
        node.add_edge_to(child)

        assert child.graph is node.graph
        assert node.uid in node.graph
        assert child.uid in node.graph

        pickled = pickle.dumps(graph)
        restored = pickle.loads(pickled)

        assert graph == restored

    def test_model_dump_uses_data_field(self):
        """Test that model_dump uses _data not data."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        dump = g.model_dump()
        assert 'data' not in dump
        assert '_data' in dump

    def test_entity_unstructure(self):
        """Test unstructuring graph via Entity.unstructure."""
        g = Graph()
        a = g.add_node(label="A")

        data = Entity.unstructure(g)
        assert 'data' not in data
        assert '_data' in data


# ============================================================================
# Graph Equality
# ============================================================================

class TestGraphEquality:
    """Tests for graph equality comparison."""

    def test_graph_equality_based_on_data(self):
        """Test that graph equality is based on data contents."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        e = g.add_edge(a, b)

        data = g.unstructure()
        g2 = Entity.structure(data)

        assert g == g2

    def test_graph_inequality_when_data_changes(self):
        """Test that modifying data makes graphs unequal."""
        g = Graph()
        a = g.add_node(label="A")
        b = g.add_node(label="B")

        data = g.unstructure()
        g2 = Entity.structure(data)

        # Initially equal
        assert g == g2

        # Modify g2
        g2.add_node(label="C")

        # Now unequal
        assert g != g2

    def test_unstructure_does_not_mutate_data(self):
        """Test that structuring doesn't mutate unstructured data."""
        g = Graph()
        a = g.add_node(label="A")

        data1 = g.unstructure()
        g2 = Graph.structure(dict(data1))
        data2 = g.unstructure()

        assert data1 == data2

    def test_structure_via_entity_or_graph(self):
        """Test structuring via Entity.structure or Graph.structure."""
        g = Graph()
        g.add_node(label="A")

        data = g.unstructure()

        # Both should work
        g1 = Entity.structure(data)
        g2 = Graph.structure(dict(data))

        assert g == g1
        assert g == g2
