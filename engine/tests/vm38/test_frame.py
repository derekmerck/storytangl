"""Contract tests for ``tangl.vm38.runtime.frame``.

Organized by concept:
- PhaseCtx: namespace caching, registry assembly
- Frame.follow_edge: pipeline execution, entry_phase skipping
- Frame.resolve_choice: redirect chaining, return stack, recursion guard
- Frame.goto_node: forced jump
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core38 import Graph, OrderedRegistry, Record
from tangl.vm38.dispatch import (
    dispatch as vm_dispatch,
    on_journal,
    on_prereqs,
    on_postreqs,
    on_update,
    on_validate,
)
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.runtime.frame import Frame, PhaseCtx
from tangl.vm38.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)


# ============================================================================
# Helpers
# ============================================================================

class SimpleFragment(Record):
    content: str = ""


def _simple_graph(*labels: str) -> tuple[Graph, list[TraversableNode]]:
    """Quick linear graph: a→b→c..."""
    g = Graph()
    nodes = [TraversableNode(label=lbl, registry=g) for lbl in labels]
    for i in range(len(nodes) - 1):
        TraversableEdge(
            registry=g,
            predecessor_id=nodes[i].uid,
            successor_id=nodes[i + 1].uid,
        )
    return g, nodes


# ============================================================================
# PhaseCtx
# ============================================================================


class TestPhaseCtx:
    def test_registries_include_vm_dispatch(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        registries = ctx.get_registries()
        # Should include at least the module-level vm_dispatch
        assert vm_dispatch in registries

    def test_ns_caching(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        a.locals = {"key": "val"}

        @on_journal  # just to have _something_ registered, ns uses gather_ns
        def _noop(*, caller, ctx, **kw):
            return None

        from tangl.vm38.dispatch import on_gather_ns
        @on_gather_ns
        def _locals(*, caller, ctx, **kw):
            if hasattr(caller, "locals") and caller.locals:
                return dict(caller.locals)

        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        ns1 = ctx.get_ns(a)
        ns2 = ctx.get_ns(a)
        # Same object — cached
        assert ns1 is ns2


# ============================================================================
# Frame.follow_edge — basic pipeline
# ============================================================================


class TestFollowEdge:
    def test_moves_cursor(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        edge = AnonymousEdge(predecessor=a, successor=b)
        frame.follow_edge(edge)
        assert frame.cursor is b

    def test_increments_cursor_steps(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert frame.cursor_steps == 1

    def test_no_redirect_returns_none(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert result is None

    def test_journal_output_appended(self) -> None:
        """Journal handler output goes to the output stream."""
        frag = SimpleFragment(content="hello")

        @on_journal
        def emit(*, caller, ctx, **kw):
            return frag

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert frag in list(frame.output_stream.values())

    def test_journal_list_output_flattened(self) -> None:
        """Journal returning a list appends each fragment."""
        f1 = SimpleFragment(content="one")
        f2 = SimpleFragment(content="two")

        @on_journal
        def emit(*, caller, ctx, **kw):
            return [f1, f2]

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        values = list(frame.output_stream.values())
        assert f1 in values and f2 in values


class TestFollowEdgeEntryPhase:
    """entry_phase controls which pipeline phases are skipped."""

    def test_entry_at_update_skips_validate_and_planning(self) -> None:
        validate_called = []

        @on_validate
        def track(*, caller, ctx, **kw):
            validate_called.append(True)
            return True

        g, [a, b] = _simple_graph("a", "b")
        edge = AnonymousEdge(
            predecessor=a, successor=b,
            entry_phase=ResolutionPhase.UPDATE,
        )
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(edge)
        assert frame.cursor is b
        # Validate should NOT have been called
        assert len(validate_called) == 0

    def test_validation_failure_raises(self) -> None:
        @on_validate
        def block(*, caller, ctx, **kw):
            return False

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        with pytest.raises(ValueError, match="validation failed"):
            frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))


class TestFollowEdgeRedirects:
    """PREREQS and POSTREQS can return edges for redirection."""

    def test_prereq_redirect(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        c = TraversableNode(label="c", registry=g)

        @on_prereqs
        def redirect_to_c(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        # follow_edge returns the redirect edge
        assert result is not None
        assert result.successor is c

    def test_postreq_redirect(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        c = TraversableNode(label="c", registry=g)

        @on_postreqs
        def redirect_to_c(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert result is not None
        assert result.successor is c


# ============================================================================
# Frame.resolve_choice — the main loop
# ============================================================================


class TestResolveChoice:
    def test_simple_move_to_leaf(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))
        assert frame.cursor is b

    def test_follows_redirect_chain(self) -> None:
        """a→b redirects to c via prereqs."""
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        c = TraversableNode(label="c", registry=g)

        @on_prereqs
        def redirect(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))
        # Lands on c after the redirect chain
        assert frame.cursor is c

    def test_recursion_guard(self) -> None:
        """Infinite redirect loop raises RecursionError."""
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)

        @on_prereqs
        def infinite_loop(*, caller, ctx, **kw):
            if caller is a:
                return AnonymousEdge(predecessor=a, successor=b)
            elif caller is b:
                return AnonymousEdge(predecessor=b, successor=a)
            return None

        frame = Frame(graph=g, cursor=a)
        with pytest.raises(RecursionError, match="exceeded"):
            frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))


class TestResolveChoiceReturnStack:
    """Call edges push to return stack; terminals pop back."""

    def test_call_and_return(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)

        # a→b is a call edge: push b, return to a at UPDATE
        call_edge = TraversableEdge(
            registry=g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )

        # When we visit b, PREREQS returns the call_edge as a redirect
        # Then when b pipeline completes (no redirect), return stack pops
        # to a at UPDATE.
        # Actually, let's set up a prereq that returns the call edge to b
        @on_prereqs
        def trigger_call(*, caller, ctx, **kw):
            if caller is a:
                return call_edge
            return None

        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=a))
        # After: a PREREQS → call_edge(a→b) pushed, follow b,
        # b completes cleanly, pop stack → return to a at UPDATE
        # Should end on a (returned)
        assert frame.cursor is a


# ============================================================================
# Frame.goto_node
# ============================================================================


class TestGotoNode:
    def test_goto_moves_cursor(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.goto_node(b)
        assert frame.cursor is b

    def test_goto_skips_validation(self) -> None:
        called = []

        @on_validate
        def block(*, caller, ctx, **kw):
            called.append(True)
            return False  # Would block normal follow_edge

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        # goto_node starts at PLANNING, skipping VALIDATE
        frame.goto_node(b)
        assert frame.cursor is b
        assert len(called) == 0
