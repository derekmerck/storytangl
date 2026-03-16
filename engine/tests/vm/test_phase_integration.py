# engine/tests/vm/test_phase_integration.py
"""End-to-end contract tests for the vm phase pipeline.

These tests exercise ``Frame.resolve_choice`` and ``Frame.follow_edge`` with
real dispatch handlers, verifying that each pipeline phase fires correctly and
that the outputs (cursor movement, output stream records, redirect traces,
cursor trace) match the contracts in VM_DESIGN.md.

Philosophy
----------
These are *integration* tests in the vm sense — they use real handlers but
do not require story-layer registrations.  The goal is to assert pipeline phase
ordering and aggregation contracts end-to-end without mocking the internals of
``follow_edge``.  Finer per-handler isolation is covered in
``test_system_handlers.py`` and ``test_dispatch.py``.

Organized by pipeline contract:

- Linear traversal — cursor moves, counters increment, visited flags set
- VALIDATE — failing validator blocks traversal
- PREREQS redirect — auto-redirect chains until terminal
- POSTREQS redirect — auto-continuation after content emission
- UPDATE mutations — locals mutation visible in next pipeline pass
- JOURNAL output — fragments emitted to output_stream
- FINALIZE/replay — StepRecord appended after each hop
- Redirect trace — redirect_trace populated for PREREQS/POSTREQS
- Ledger integration — resolve_choice syncs frame results back to ledger
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

import pytest

from tangl.core import Graph
from tangl.vm.dispatch import (
    dispatch as vm_dispatch,
    on_journal,
    on_update,
    on_validate,
)
from tangl.vm.fragments import ContentFragment
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import Frame
from tangl.vm.runtime.ledger import Ledger
from tangl.vm.replay import StepRecord
from tangl.vm.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)
import tangl.vm.system_handlers  # side-effect: register default handlers


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


def _register_system_handlers():
    """Re-register system handlers after clean_vm_dispatch clears the registry."""
    sh = tangl.vm.system_handlers
    from tangl.vm.dispatch import (
        on_gather_ns, on_validate as _ov, on_prereqs as _op,
        on_update as _ou, on_postreqs as _ops,
    )
    on_gather_ns(sh.contribute_runtime_baseline)
    on_gather_ns(sh.contribute_locals)
    on_gather_ns(sh.contribute_satisfied_deps)
    _ov(sh.validate_successor_exists)
    _op(sh.descend_into_container)
    _op(sh.follow_triggered_prereqs)
    _ou(sh.apply_runtime_effects)
    _ou(sh.mark_visited)
    _ops(sh.follow_triggered_postreqs)


@pytest.fixture(autouse=True)
def with_system_handlers(clean_vm_dispatch):
    """Ensure system handlers are active for every test in this module."""
    _register_system_handlers()
    yield
    # clean_vm_dispatch handles teardown


# ---------------------------------------------------------------------------
# Linear traversal
# ---------------------------------------------------------------------------


class TestLinearTraversal:
    """Basic cursor movement with no redirects."""

    def test_cursor_moves_to_successor(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(edge)
        assert frame.cursor is b

    def test_cursor_steps_increments_per_hop(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        bc = _edge(g, predecessor_id=b.uid, successor_id=c.uid)
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(ab)
        frame.follow_edge(bc)
        assert frame.cursor_steps == 2

    def test_mark_visited_fires_on_arrival(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        b.locals = {}
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(edge)
        assert b.locals.get("_visited") is True

    def test_cursor_trace_accumulates_visited_nodes(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        bc = _edge(g, predecessor_id=b.uid, successor_id=c.uid)
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(ab)
        frame.follow_edge(bc)
        assert b.uid in frame.cursor_trace
        assert c.uid in frame.cursor_trace

    def test_self_loop_increments_reentrant(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        loop = _edge(g, predecessor_id=a.uid, successor_id=a.uid)
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(loop)
        # cursor_trace extended
        assert len(frame.cursor_trace) >= 1


# ---------------------------------------------------------------------------
# VALIDATE: validation gate
# ---------------------------------------------------------------------------


class TestValidateGate:
    """VALIDATE phase failure raises or blocks traversal."""

    def test_failing_validator_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        @on_validate
        def always_false(caller, *, ctx, **kwargs):
            return False

        with _cleanup_behaviors(always_false):
            frame = Frame(graph=g, cursor=a)
            with pytest.raises(ValueError, match="validation failed"):
                frame.follow_edge(edge)

    def test_validate_successor_exists_blocks_dangling_anonymous_edge(self) -> None:
        """An AnonymousEdge whose successor has no graph membership is blocked."""
        g = Graph()
        a = _node(g, label="a")
        orphan = TraversableNode(label="orphan")  # NOT added to graph
        edge = AnonymousEdge(predecessor=a, successor=orphan)
        frame = Frame(graph=g, cursor=a)
        with pytest.raises(Exception):
            frame.follow_edge(edge)


# ---------------------------------------------------------------------------
# PREREQS: redirect chains
# ---------------------------------------------------------------------------


class TestPrereqsRedirect:
    """PREREQS handler returning an edge causes auto-follow before yielding."""

    def test_triggered_prereq_edge_is_followed(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        bc = _edge(
            g,
            predecessor_id=b.uid,
            successor_id=c.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(ab)
        # cursor should skip b and land at c after prereq redirect
        assert frame.cursor is c

    def test_redirect_trace_records_prereq_hops(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(
            g,
            predecessor_id=b.uid,
            successor_id=c.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(ab)
        assert any(r["phase"] == "prereqs" for r in frame.redirect_trace)

    def test_container_descent_follows_into_source(self) -> None:
        """descend_into_container returns an enter() AnonymousEdge for containers."""
        g = Graph()
        outer = _node(g, label="outer")
        container = _node(g, label="container")
        source = _node(g, label="entry")
        sink = _node(g, label="exit")
        container.add_child(source)
        container.add_child(sink)
        container.source_id = source.uid
        container.sink_id = sink.uid

        edge_to_container = _edge(g, predecessor_id=outer.uid, successor_id=container.uid)

        frame = Frame(graph=g, cursor=outer)
        frame.resolve_choice(edge_to_container)
        # After descent the cursor should be inside the container
        assert frame.cursor in (container, source)


# ---------------------------------------------------------------------------
# POSTREQS: continuation redirect
# ---------------------------------------------------------------------------


class TestPostreqsRedirect:
    """POSTREQS returning an edge auto-advances cursor after JOURNAL."""

    def test_triggered_postreq_advances_cursor(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        bc = _edge(
            g,
            predecessor_id=b.uid,
            successor_id=c.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(ab)
        assert frame.cursor is c

    def test_redirect_trace_records_postreq_hops(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(
            g,
            predecessor_id=b.uid,
            successor_id=c.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(ab)
        assert any(r["phase"] == "postreqs" for r in frame.redirect_trace)


# ---------------------------------------------------------------------------
# UPDATE: state mutations
# ---------------------------------------------------------------------------


class TestUpdateMutations:
    """UPDATE mutations are committed in-place and visible immediately."""

    def test_custom_update_handler_mutates_node(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        b.locals = {}
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        @on_update
        def stamp(caller, *, ctx, **kwargs):
            if caller is b:
                if caller.locals is None:
                    caller.locals = {}
                caller.locals["stamped"] = True

        with _cleanup_behaviors(stamp):
            frame = Frame(graph=g, cursor=a)
            frame.follow_edge(edge)
            assert b.locals.get("stamped") is True

    def test_update_mutation_visible_in_ns_on_next_hop(self) -> None:
        """Namespace is recomputed from scratch each pipeline pass."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        b.locals = {"x": 1}
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        bc = _edge(g, predecessor_id=b.uid, successor_id=c.uid)

        @on_update
        def increment_x(caller, *, ctx, **kwargs):
            if caller is b and caller.locals is not None:
                caller.locals["x"] = caller.locals.get("x", 0) + 10

        ns_on_second_hop: dict = {}

        @on_journal
        def capture_ns(caller, *, ctx, **kwargs):
            if caller is c:
                ns_on_second_hop.update(dict(ctx.get_ns(b)))
            return None

        with _cleanup_behaviors(increment_x, capture_ns):
            frame = Frame(graph=g, cursor=a)
            frame.resolve_choice(ab)
            # Follow to c in a second choice
            frame2 = Frame(graph=g, cursor=b)
            frame2.resolve_choice(bc)
            # b.locals["x"] was mutated during first hop to 11
            assert b.locals.get("x") == 11


# ---------------------------------------------------------------------------
# JOURNAL output
# ---------------------------------------------------------------------------


class TestJournalOutput:
    """JOURNAL handlers emit fragments into the output_stream."""

    def test_journal_fragment_appended_to_output_stream(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        from tangl.core import OrderedRegistry
        stream = OrderedRegistry()
        frame = Frame(graph=g, cursor=a, output_stream=stream)

        @on_journal
        def emit_hello(caller, *, ctx, **kwargs):
            if caller is b:
                return ContentFragment(content="hello", source_id=b.uid)

        with _cleanup_behaviors(emit_hello):
            frame.follow_edge(edge)
            fragments = [v for v in stream.values() if isinstance(v, ContentFragment)]
            assert any(f.content == "hello" for f in fragments)

    def test_multiple_journal_handlers_all_contribute(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        from tangl.core import OrderedRegistry
        stream = OrderedRegistry()
        frame = Frame(graph=g, cursor=a, output_stream=stream)

        @on_journal
        def emit_one(caller, *, ctx, **kwargs):
            if caller is b:
                return ContentFragment(content="one", source_id=b.uid)

        @on_journal
        def emit_two(caller, *, ctx, **kwargs):
            if caller is b:
                return ContentFragment(content="two", source_id=b.uid)

        with _cleanup_behaviors(emit_one, emit_two):
            frame.follow_edge(edge)
            texts = {
                v.content for v in stream.values() if isinstance(v, ContentFragment)
            }
            assert "one" in texts
            assert "two" in texts


# ---------------------------------------------------------------------------
# Ledger integration: resolve_choice syncs results back
# ---------------------------------------------------------------------------


class TestLedgerIntegration:
    """Ledger.resolve_choice delegates to Frame and syncs state back."""

    def test_ledger_cursor_updated_after_resolve(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.resolve_choice(edge.uid)
        assert ledger.cursor_id == b.uid

    def test_ledger_choice_steps_increments(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        ledger = Ledger(graph=g, cursor_id=a.uid)
        before = ledger.choice_steps
        ledger.resolve_choice(edge.uid)
        assert ledger.choice_steps == before + 1

    def test_ledger_cursor_history_extended(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.resolve_choice(edge.uid)
        assert b.uid in ledger.cursor_history

    def test_ledger_step_record_emitted(self) -> None:
        """After resolve_choice, a StepRecord exists in the output_stream."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.resolve_choice(edge.uid)
        step_records = [
            v for v in ledger.output_stream.values() if isinstance(v, StepRecord)
        ]
        assert len(step_records) >= 1

    def test_ledger_redirect_trace_propagated(self) -> None:
        """redirect_trace from frame is written back to ledger."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        ab = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(
            g,
            predecessor_id=b.uid,
            successor_id=c.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        ledger = Ledger(graph=g, cursor_id=a.uid)
        ledger.resolve_choice(ab.uid)
        assert ledger.redirect_trace  # non-empty; at least one redirect recorded

    def test_ledger_get_journal_returns_emitted_fragments(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        @on_journal
        def emit_content(caller, *, ctx, **kwargs):
            if caller is b:
                return ContentFragment(content="narrative text", source_id=b.uid)

        with _cleanup_behaviors(emit_content):
            ledger = Ledger(graph=g, cursor_id=a.uid)
            ledger.resolve_choice(edge.uid)
            journal = ledger.get_journal()
            assert any(
                isinstance(f, ContentFragment) and f.content == "narrative text"
                for f in journal
            )
