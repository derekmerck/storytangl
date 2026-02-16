"""Contract tests for ``tangl.vm38.runtime.ledger``.

Organized by concept:
- Cursor management: cursor property, cursor_id tracking
- Call stack: push_call / pop_call
- Frame creation: get_frame produces a Frame with shared state
- Choice resolution: resolve_choice delegates to frame and syncs state
"""

from __future__ import annotations

import pytest

from tangl.core38 import Graph
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.runtime.frame import Frame
from tangl.vm38.runtime.ledger import Ledger
from tangl.vm38.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
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
# Helpers
# ============================================================================


def _make_ledger(*labels: str) -> tuple[Ledger, list[TraversableNode]]:
    """Build a ledger with a linear graph and cursor at the first node."""
    g = Graph()
    nodes = [_node(g, label=lbl) for lbl in labels]
    for i in range(len(nodes) - 1):
        _edge(g, predecessor_id=nodes[i].uid,
            successor_id=nodes[i + 1].uid,
        )
    ledger = Ledger(graph=g, cursor_id=nodes[0].uid)
    return ledger, nodes


# ============================================================================
# Cursor management
# ============================================================================


class TestLedgerCursor:
    def test_cursor_property_resolves_from_graph(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        assert ledger.cursor is a
        assert ledger.cursor_id == a.uid

    def test_cursor_setter_updates_id(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        ledger.cursor = b
        assert ledger.cursor_id == b.uid


# ============================================================================
# Call stack
# ============================================================================


class TestLedgerCallStack:
    def test_push_call_requires_return_phase(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
        )
        ledger = Ledger(graph=g, cursor_id=a.uid)
        with pytest.raises(ValueError):
            ledger.push_call(edge)

    def test_push_and_pop(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.push_call(call_edge)
        popped = ledger.pop_call()
        assert popped is call_edge

    def test_empty_pop_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ledger = Ledger(graph=g, cursor_id=a.uid)
        with pytest.raises(IndexError):
            ledger.pop_call()


# ============================================================================
# Frame creation
# ============================================================================


class TestLedgerGetFrame:
    def test_returns_frame(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        frame = ledger.get_frame()
        assert isinstance(frame, Frame)
        assert frame.graph is ledger.graph
        assert frame.cursor is a


# ============================================================================
# Choice resolution
# ============================================================================


class TestLedgerResolveChoice:
    def test_resolve_updates_cursor(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        g = ledger.graph
        edge = list(a.edges_out())[0]
        ledger.resolve_choice(edge.uid)
        assert ledger.cursor is b

    def test_resolve_increments_counters(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        initial_choice = ledger.choice_steps
        edge = list(a.edges_out())[0]
        ledger.resolve_choice(edge.uid)
        assert ledger.choice_steps == initial_choice + 1
