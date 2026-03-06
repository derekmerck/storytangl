"""Contract tests for ``tangl.core.graph``."""

from __future__ import annotations

import pickle

import pytest

from tangl.core.graph import Edge, Graph, GraphItem, HierarchicalNode, Node, Subgraph
from tangl.core.selector import Selector


class SubclassNode(Node):
    pass


class WeightedEdge(Edge):
    weight: float = 1.0


class SubclassSubgraph(Subgraph):
    pass


class TestGraphCreationAndFind:
    def test_add_node_and_edge(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        edge = graph.add_edge(a, b, label="ab")
        assert isinstance(a, Node)
        assert edge.predecessor is a and edge.successor is b

    def test_add_node_custom_kind(self) -> None:
        graph = Graph()
        node = graph.add_node(kind=SubclassNode, label="x")
        assert isinstance(node, SubclassNode)

    def test_add_edge_custom_kind(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        edge = graph.add_edge(a, b, kind=WeightedEdge, weight=2.5)
        assert isinstance(edge, WeightedEdge)
        assert edge.weight == 2.5

    def test_add_edge_dangling_endpoints(self) -> None:
        graph = Graph()
        b = graph.add_node(label="b")
        edge = graph.add_edge(None, b)
        assert edge.predecessor is None
        assert edge.successor is b

    def test_add_subgraph_with_members(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        sg = graph.add_subgraph(members=[a, b], label="sg")
        assert list(sg.members()) == [a, b]

    def test_find_typed_helpers(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        e = graph.add_edge(a, b)
        s = graph.add_subgraph(label="s")
        assert graph.nodes == [a, b]
        assert graph.edges == [e]
        assert graph.subgraphs == [s]
        assert graph.find_node(Selector(label="a")) is a
        assert graph.find_edge(Selector(predecessor=a)) is e
        assert graph.find_subgraph(Selector(label="s")) is s


class TestEdgeAndNode:
    def test_add_edge_from_direction(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        edge = a.add_edge_from(b)
        assert edge.predecessor is b
        assert edge.successor is a

    def test_node_edge_navigation(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        c = graph.add_node(label="c")
        ab = graph.add_edge(a, b)
        cb = graph.add_edge(c, b)
        assert set(x.uid for x in b.edges_in()) == {ab.uid, cb.uid}
        assert list(a.edges_out()) == [ab]
        assert set(x.uid for x in b.predecessors()) == {a.uid, c.uid}

    def test_remove_edge_helpers(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        a.add_edge_to(b)
        assert graph.find_edge(Selector(predecessor=a, successor=b)) is not None
        a.remove_edge_to(b)
        assert graph.find_edge(Selector(predecessor=a, successor=b)) is None

    def test_edge_repr_dangling(self) -> None:
        graph = Graph()
        edge = Edge(registry=graph)
        assert "anon->anon" in repr(edge)


class TestGraphItemHierarchyAndSerialization:
    def test_graph_item_alias(self) -> None:
        graph = Graph()
        node = Node(label="n")
        graph.add(node)
        assert isinstance(node, GraphItem)
        assert node.graph is graph

    def test_hierarchical_node_reparenting(self) -> None:
        graph = Graph()
        root = HierarchicalNode(label="root", registry=graph)
        left = HierarchicalNode(label="left", registry=graph)
        right = HierarchicalNode(label="right", registry=graph)
        root.add_child(left)
        assert left.path == "root.left"
        right.add_child(left)
        assert left.parent is right
        assert left.path == "right.left"

    def test_graph_roundtrip_preserves_topology(self) -> None:
        graph = Graph(label="g")
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        e = graph.add_edge(a, b, label="ab")
        sg = graph.add_subgraph(label="s", members=[a])

        restored = Graph.structure(graph.unstructure())
        restored_edge = restored.find_edge(Selector(label="ab"))
        restored_subgraph = restored.find_subgraph(Selector(label="s"))

        assert restored.label == "g"
        assert restored_edge.predecessor.get_label() == "a"
        assert restored_edge.successor.get_label() == "b"
        assert len(list(restored_subgraph.members())) == 1
        assert restored == graph

    def test_graph_pickle_roundtrip(self) -> None:
        graph = Graph(label="g")
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        graph.add_edge(a, b)
        restored = pickle.loads(pickle.dumps(graph))
        assert restored == graph

    def test_add_edge_validates_linkable(self) -> None:
        graph = Graph()
        other = Graph()
        a = graph.add_node(label="a")
        b = other.add_node(label="b")
        with pytest.raises(ValueError):
            graph.add_edge(a, b)


class TestGraphValueHashContracts:
    def test_value_hash_is_stable_for_unchanged_graph(self) -> None:
        graph = Graph(label="g")
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        graph.add_edge(a, b, label="ab")

        first = graph.value_hash()
        second = graph.value_hash()
        assert first == second

    def test_value_hash_changes_for_graph_membership_mutations(self) -> None:
        graph = Graph(label="g")
        baseline = graph.value_hash()

        node = graph.add_node(label="a")
        after_add = graph.value_hash()
        assert after_add != baseline

        graph.remove(node.uid)
        after_remove = graph.value_hash()
        assert after_remove != after_add
        assert after_remove == baseline

    def test_value_hash_changes_when_member_data_changes(self) -> None:
        graph = Graph(label="g")
        node = graph.add_node(label="a")
        before = graph.value_hash()
        node.label = "renamed"
        after = graph.value_hash()
        assert after != before

    def test_value_hash_preserved_through_unstructure_structure_roundtrip(self) -> None:
        graph = Graph(label="g")
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        graph.add_edge(a, b, label="ab")

        restored = Graph.structure(graph.unstructure())
        assert restored.value_hash() == graph.value_hash()
