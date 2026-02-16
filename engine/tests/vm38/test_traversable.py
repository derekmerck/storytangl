"""Contract tests for ``tangl.vm38.traversable``.

Organized by concept:
- LCA utilities: lca(), decompose_move()
- TraversableNode: container/leaf duality, enter(), hierarchy
- TraversableEdge: entry_phase, return_phase, get_return_edge()
- AnonymousEdge: lightweight construction, interface compatibility
"""

from __future__ import annotations

import pytest

from tangl.core38 import Graph
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.traversable import (
    AnonymousEdge,
    AnyTraversableEdge,
    TraversableEdge,
    TraversableNode,
    decompose_move,
    lca,
)


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge


# ============================================================================
# LCA
# ============================================================================


class TestLCA:
    """Lowest common ancestor of two nodes in a hierarchy."""

    def test_same_node(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        assert lca(a, a) is a

    def test_siblings_share_parent(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(a)
        root.add_child(b)
        assert lca(a, b) is root

    def test_parent_child(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)
        assert lca(parent, child) is parent

    def test_cousins(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        ch1 = _node(g, label="ch1")
        ch2 = _node(g, label="ch2")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(ch1)
        root.add_child(ch2)
        ch1.add_child(a)
        ch2.add_child(b)
        assert lca(a, b) is root

    def test_disjoint_returns_none(self) -> None:
        g1 = Graph()
        g2 = Graph()
        a = _node(g1, label="a")
        b = _node(g2, label="b")
        assert lca(a, b) is None


# ============================================================================
# decompose_move
# ============================================================================


class TestDecomposeMove:
    """Move decomposition into exit/enter paths around the LCA."""

    def test_cross_branch_move(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        ch1 = _node(g, label="ch1")
        ch2 = _node(g, label="ch2")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(ch1)
        root.add_child(ch2)
        ch1.add_child(a)
        ch2.add_child(b)

        exit_path, enter_path, pivot = decompose_move(a, b)
        assert [n.label for n in exit_path] == ["a", "ch1"]
        assert [n.label for n in enter_path] == ["ch2", "b"]
        assert pivot is root

    def test_sibling_move(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        a = _node(g, label="a")
        c = _node(g, label="c")
        parent.add_child(a)
        parent.add_child(c)

        ex, en, pivot = decompose_move(a, c)
        assert [n.label for n in ex] == ["a"]
        assert [n.label for n in en] == ["c"]
        assert pivot is parent

    def test_descent_into_child(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)

        ex, en, pivot = decompose_move(parent, child)
        assert ex == []
        assert [n.label for n in en] == ["c"]
        assert pivot is parent

    def test_ascent_to_parent(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)

        ex, en, pivot = decompose_move(child, parent)
        assert [n.label for n in ex] == ["c"]
        assert en == []
        assert pivot is parent

    def test_disjoint_raises(self) -> None:
        g1 = Graph()
        g2 = Graph()
        a = _node(g1, label="a")
        b = _node(g2, label="b")
        with pytest.raises(ValueError, match="no common ancestor"):
            decompose_move(a, b)


# ============================================================================
# TraversableNode — container/leaf duality
# ============================================================================


class TestTraversableNodeLeaf:
    """Leaf nodes — no container structure."""

    def test_leaf_is_not_container(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        assert not node.is_container

    def test_leaf_enter_raises(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        with pytest.raises(ValueError, match="not a container"):
            node.enter()

    def test_source_none_for_leaf(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        assert node.source is None


class TestTraversableNodeContainer:
    """Container nodes with designated source/sink members."""

    def test_is_container_when_source_set(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid
        assert container.is_container

    def test_enter_returns_anonymous_edge(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid

        edge = container.enter()
        assert isinstance(edge, AnonymousEdge)
        assert edge.predecessor is container
        assert edge.successor is entry

    def test_sink_property(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        exit_node = _node(g, label="exit")
        container.add_child(entry)
        container.add_child(exit_node)
        container.source_id = entry.uid
        container.sink_id = exit_node.uid

        assert container.source is entry
        assert container.sink is exit_node

    def test_has_forward_progress_stub(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        # MVP stub always returns True
        assert a.has_forward_progress(b)


# ============================================================================
# TraversableEdge
# ============================================================================


class TestTraversableEdge:
    """Persistent graph edge with traversal metadata."""

    def test_default_phases_are_none(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert e.entry_phase is None
        assert e.return_phase is None
        assert e.trigger_phase is None

    def test_entry_phase_set(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            entry_phase=ResolutionPhase.UPDATE,
        )
        assert e.entry_phase == ResolutionPhase.UPDATE

    def test_call_edge_return(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ret = call.get_return_edge()
        assert isinstance(ret, AnonymousEdge)
        assert ret.successor is a
        assert ret.entry_phase == ResolutionPhase.UPDATE

    def test_non_call_edge_return_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        with pytest.raises(ValueError, match="not a call edge"):
            e.get_return_edge()

    def test_trigger_phase_for_auto_redirect(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        assert e.trigger_phase == ResolutionPhase.PREREQS

    def test_predecessor_successor_narrowing(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert e.predecessor is a
        assert e.successor is b


# ============================================================================
# AnonymousEdge
# ============================================================================


class TestAnonymousEdge:
    """Lightweight transient edge — no graph, no UUID."""

    def test_minimal_construction(self) -> None:
        g = Graph()
        b = _node(g, label="b")
        e = AnonymousEdge(successor=b)
        assert e.successor is b
        assert e.predecessor is None
        assert e.entry_phase is None

    def test_full_construction(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = AnonymousEdge(predecessor=a, successor=b, entry_phase=ResolutionPhase.UPDATE)
        assert e.predecessor is a
        assert e.successor is b
        assert e.entry_phase == ResolutionPhase.UPDATE

    def test_repr_includes_labels(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = AnonymousEdge(predecessor=a, successor=b)
        r = repr(e)
        assert "a" in r and "b" in r

    def test_no_return_phase(self) -> None:
        """AnonymousEdge is never a call edge — no return_phase attribute."""
        g = Graph()
        b = _node(g, label="b")
        e = AnonymousEdge(successor=b)
        assert not hasattr(e, "return_phase")
