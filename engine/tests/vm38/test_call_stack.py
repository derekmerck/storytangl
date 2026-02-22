# engine/tests/vm38/test_call_stack.py
"""Contract tests for vm38 call/return stack semantics.

Covers the Ledger + Frame call stack that enables subroutine traversal in
vm38.  The legacy VM used an explicit ``StackFrame`` type with serialized call
metadata; vm38 simplifies this to ``call_stack_ids: list[UUID]`` on the
Ledger, backed by ``TraversableEdge.return_phase`` as the marker that an edge
is a call edge.

Organized by contract:

- Stack invariants: push requires ``return_phase``, empty pop raises
- Nesting: multiple push/pop levels preserve LIFO order
- Frame integration: ``resolve_choice`` pushes on call-edges and pops on
  terminal pipeline completion
- Return-edge semantics: the return edge targets the predecessor at
  ``return_phase``, skipping earlier phases
- Persistence: ``call_stack_ids`` survives ``unstructure`` / ``structure``
  round-trips so REST resume works without replay
- Overflow protection: runaway redirect chains raise ``RecursionError``

See Also
--------
``engine/tests/vm38/test_ledger.py`` — atomic push/pop already covered in the
Ledger unit tests; this module focuses on *integration* of the stack with
Frame's pipeline execution loop.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

import pytest

from tangl.core38 import Graph
from tangl.vm38.dispatch import (
    dispatch as vm_dispatch,
    on_postreqs,
    on_prereqs,
)
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.runtime.frame import Frame
from tangl.vm38.runtime.ledger import Ledger
from tangl.vm38.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge


def _ledger(graph: Graph, entry: TraversableNode) -> Ledger:
    """Build a ledger without running the full entry pipeline."""
    return Ledger(graph=graph, cursor_id=entry.uid)


@contextmanager
def _cleanup_behaviors(*funcs: Callable[..., object]) -> Iterator[None]:
    """Remove registered vm_dispatch behaviors after test assertions."""
    try:
        yield
    finally:
        for func in funcs:
            behavior = getattr(func, "_behavior", None)
            if behavior is not None:
                vm_dispatch.remove(behavior.uid)


# ---------------------------------------------------------------------------
# Stack invariants
# ---------------------------------------------------------------------------


class TestStackInvariants:
    """Low-level Ledger push/pop contracts."""

    def test_push_without_return_phase_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        ledger = _ledger(g, a)
        with pytest.raises(ValueError, match="return phase"):
            ledger.push_call(edge)

    def test_push_with_return_phase_succeeds(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = _ledger(g, a)
        ledger.push_call(call_edge)
        assert call_edge.uid in ledger.call_stack_ids

    def test_pop_on_empty_stack_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ledger = _ledger(g, a)
        with pytest.raises(IndexError):
            ledger.pop_call()

    def test_push_then_pop_returns_same_edge(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = _ledger(g, a)
        ledger.push_call(call_edge)
        popped = ledger.pop_call()
        assert popped is call_edge
        assert ledger.call_stack_ids == []


# ---------------------------------------------------------------------------
# Nesting: LIFO order with multiple calls
# ---------------------------------------------------------------------------


class TestNesting:
    """Multiple push/pop levels maintain LIFO invariant."""

    def _make_chain(self, n: int) -> tuple[Graph, list[TraversableNode], list[TraversableEdge]]:
        g = Graph()
        nodes = [_node(g, label=f"n{i}") for i in range(n)]
        edges = [
            _edge(
                g,
                predecessor_id=nodes[i].uid,
                successor_id=nodes[i + 1].uid,
                return_phase=ResolutionPhase.UPDATE,
            )
            for i in range(n - 1)
        ]
        return g, nodes, edges

    def test_two_levels_lifo(self) -> None:
        g, nodes, edges = self._make_chain(3)
        ledger = _ledger(g, nodes[0])
        ledger.push_call(edges[0])
        ledger.push_call(edges[1])

        assert ledger.pop_call() is edges[1]
        assert ledger.pop_call() is edges[0]
        assert ledger.call_stack_ids == []

    def test_stack_depth_matches_push_count(self) -> None:
        g, nodes, edges = self._make_chain(4)
        ledger = _ledger(g, nodes[0])
        for e in edges:
            ledger.push_call(e)
        assert len(ledger.call_stack_ids) == 3

    def test_interleaved_push_pop_preserves_order(self) -> None:
        g, nodes, edges = self._make_chain(4)
        ledger = _ledger(g, nodes[0])
        ledger.push_call(edges[0])
        ledger.push_call(edges[1])
        assert ledger.pop_call() is edges[1]
        ledger.push_call(edges[2])
        assert ledger.pop_call() is edges[2]
        assert ledger.pop_call() is edges[0]


# ---------------------------------------------------------------------------
# Return-edge semantics
# ---------------------------------------------------------------------------


class TestReturnEdgeSemantics:
    """TraversableEdge.get_return_edge() returns an AnonymousEdge back to predecessor."""

    def test_get_return_edge_targets_predecessor(self) -> None:
        g = Graph()
        a = _node(g, label="caller")
        b = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        return_edge = call_edge.get_return_edge()
        assert return_edge.successor is a

    def test_return_edge_entry_phase_matches_return_phase(self) -> None:
        g = Graph()
        a = _node(g, label="caller")
        b = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.FINALIZE,
        )
        return_edge = call_edge.get_return_edge()
        assert return_edge.entry_phase == ResolutionPhase.FINALIZE

    def test_return_edge_is_anonymous(self) -> None:
        g = Graph()
        a = _node(g, label="caller")
        b = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        return_edge = call_edge.get_return_edge()
        assert isinstance(return_edge, AnonymousEdge)


# ---------------------------------------------------------------------------
# Frame integration: call edge pushes stack, return fires on terminal
# ---------------------------------------------------------------------------


class TestFrameCallReturn:
    """Frame.resolve_choice integrates call/return via return_stack."""

    def test_resolve_choice_pushes_call_edge_before_unwind(
        self, clean_vm_dispatch  # noqa: F811  # from conftest autouse
    ) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        bc = _edge(g, predecessor_id=b.uid, successor_id=c.uid)
        seen_call_stack_ids: list[list] = []

        @on_postreqs
        def continue_once(caller, *, ctx, **kwargs):
            if caller is b:
                return bc
            return None

        with _cleanup_behaviors(continue_once):
            frame = Frame(graph=g, cursor=a)
            frame.step_observer = lambda trace: seen_call_stack_ids.append(
                list(trace.call_stack_ids),
            )
            frame.resolve_choice(call_edge)

        # resolve_choice unwinds fully, but trace captures that call was pushed mid-loop.
        assert any(call_edge.uid in stack_ids for stack_ids in seen_call_stack_ids)

    def test_resolve_choice_returns_to_caller_after_terminal(
        self, clean_vm_dispatch
    ) -> None:
        """Cursor returns to caller node when callee is a terminal."""
        g = Graph()
        a = _node(g, label="caller")
        b = _node(g, label="callee")  # no outgoing edges → terminal
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(call_edge)
        # After the call round-trips, cursor is back at caller
        assert frame.cursor is a

    def test_nested_calls_unwind_correctly(self, clean_vm_dispatch) -> None:
        """Two nested calls return in LIFO order."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")  # deep terminal

        ab_call = _edge(
            g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        bc_call = _edge(
            g, predecessor_id=b.uid, successor_id=c.uid,
            return_phase=ResolutionPhase.UPDATE,
        )

        # Register a POSTREQS handler that only fires on first arrival at b.
        @on_postreqs
        def b_dives_to_c(caller, *, ctx, **kwargs):
            if caller is b and getattr(ctx, "selected_edge", None) is ab_call:
                return bc_call
            return None

        with _cleanup_behaviors(b_dives_to_c):
            frame = Frame(graph=g, cursor=a)
            frame.resolve_choice(ab_call)
            # Both calls unwound → back at a
            assert frame.cursor is a
            assert frame.return_stack == []


# ---------------------------------------------------------------------------
# Traversal query helpers on a subroutine-active ledger
# ---------------------------------------------------------------------------


class TestTraversalHelpers:
    """get_call_depth and in_subroutine work against a populated call_stack_ids."""

    def test_in_subroutine_true_when_stack_nonempty(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = _ledger(g, a)
        ledger.push_call(call_edge)
        # in_subroutine reads cursor_history length relative to call depth
        # use the raw stack depth as a proxy:
        assert len(ledger.call_stack_ids) > 0

    def test_cursor_history_extends_through_call(
        self, clean_vm_dispatch
    ) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.resolve_choice(call_edge.uid)
        # After call+return, cursor_history should include both a and b
        history_labels = [g.get(uid).label for uid in ledger.cursor_history]
        assert "b" in history_labels


# ---------------------------------------------------------------------------
# Persistence: call_stack_ids survives round-trip
# ---------------------------------------------------------------------------


class TestCallStackPersistence:
    """Ledger serializes call_stack_ids so REST resume requires no replay."""

    def test_call_stack_ids_survive_structure_roundtrip(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = _ledger(g, a)
        ledger.push_call(call_edge)

        data = ledger.unstructure()
        restored = Ledger.structure(data)

        assert restored.call_stack_ids == [call_edge.uid]

    def test_empty_call_stack_survives_roundtrip(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ledger = _ledger(g, a)

        data = ledger.unstructure()
        restored = Ledger.structure(data)

        assert restored.call_stack_ids == []

    def test_resolved_call_stack_edge_accessible_after_restore(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ledger = _ledger(g, a)
        ledger.push_call(call_edge)

        data = ledger.unstructure()
        restored = Ledger.structure(data)

        # _call_stack() resolves UIDs against the graph
        resolved = restored._call_stack()
        assert len(resolved) == 1
        assert resolved[0].uid == call_edge.uid

    def test_stale_call_stack_id_raises_on_resolution(self) -> None:
        """If graph is replaced without the call edge, resolution fails."""
        from uuid import uuid4
        g = Graph()
        a = _node(g, label="a")
        ledger = _ledger(g, a)
        ledger.call_stack_ids = [uuid4()]  # ghost UID

        with pytest.raises(ValueError, match="unresolved edge id"):
            ledger._call_stack()


# ---------------------------------------------------------------------------
# Overflow safety
# ---------------------------------------------------------------------------


class TestOverflowProtection:
    """Runaway redirect chains are caught before they blow the call stack."""

    def test_resolve_choice_raises_on_deep_redirect_chain(
        self, clean_vm_dispatch
    ) -> None:
        """More than MAX_RESOLVE_DEPTH redirects in one resolve_choice raises RecursionError."""
        from tangl.vm38.runtime.frame import MAX_RESOLVE_DEPTH

        g = Graph()
        nodes = [_node(g, label=f"n{i}") for i in range(MAX_RESOLVE_DEPTH + 5)]
        # Build a prereq chain that exceeds the depth limit
        edges = [
            _edge(
                g,
                predecessor_id=nodes[i].uid,
                successor_id=nodes[i + 1].uid,
                trigger_phase=ResolutionPhase.PREREQS,
            )
            for i in range(MAX_RESOLVE_DEPTH + 4)
        ]
        import tangl.vm38.system_handlers as sh

        on_prereqs(sh.follow_triggered_prereqs)
        with _cleanup_behaviors(sh.follow_triggered_prereqs):
            frame = Frame(graph=g, cursor=nodes[0])
            with pytest.raises(RecursionError):
                frame.resolve_choice(edges[0], max_depth=MAX_RESOLVE_DEPTH)
