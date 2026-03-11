"""Contract tests for ``tangl.vm.runtime.ledger``.

Organized by concept:
- Cursor management: cursor property, cursor_id tracking
- Call stack: push_call / pop_call
- Frame creation: get_frame produces a Frame with shared state
- Choice resolution: resolve_choice delegates to frame and syncs state
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import Graph, Selector, Snapshot
from tangl.vm.dispatch import on_prereqs
from tangl.vm.replay import CausalityTransitionRecord, RollbackRecord, StepRecord
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import Frame
from tangl.vm.runtime.causality import CausalityMode
from tangl.vm.runtime.ledger import Ledger
from tangl.vm.traversal import get_visit_count
from tangl.vm.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)
from tangl.vm.fragments import ChoiceFragment, ContentFragment


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

    def test_from_graph_initializes_with_entry_cursor_id(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        _node(g, label="b")

        ledger = Ledger.from_graph(graph=g, entry_id=a.uid)
        assert ledger.cursor_id == a.uid
        assert ledger.cursor is a
        assert ledger.cursor_history == [a.uid]
        assert ledger.choice_steps == 0
        assert ledger.cursor_steps == 0

    def test_initialize_ledger_updates_call_stack_ids(self, monkeypatch) -> None:
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

        class _FrameWithReturn:
            return_stack = [call_edge]

        monkeypatch.setattr(Ledger, "get_frame", lambda self: _FrameWithReturn())
        ledger.initialize_ledger(entry_id=a.uid)
        assert ledger.call_stack_ids == [call_edge.uid]

    def test_fresh_construction_initializes_counters(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ledger = Ledger(graph=g, cursor_id=a.uid)
        assert ledger.cursor_steps == 0
        assert ledger.choice_steps == 0
        assert ledger.reentrant_steps == 0
        assert ledger.cursor_history == [a.uid]


class TestLedgerCausality:
    def test_mark_soft_dirty_records_single_transition(self) -> None:
        ledger, _ = _make_ledger("a", "b")

        assert ledger.mark_soft_dirty("debug_check_expr", step_id="node-1") is True
        assert ledger.mark_soft_dirty("debug_check_expr", step_id="node-1") is False
        assert ledger.causality_mode == CausalityMode.SOFT_DIRTY

        transitions = list(Selector(has_kind=CausalityTransitionRecord).filter(ledger.output_stream))
        assert len(transitions) == 1
        transition = transitions[0]
        assert transition.from_mode == CausalityMode.CLEAN.value
        assert transition.to_mode == CausalityMode.SOFT_DIRTY.value
        assert transition.reason == "debug_check_expr"
        assert transition.step_id == "node-1"

    def test_escalate_to_hard_dirty_is_monotonic_and_recorded_once(self) -> None:
        ledger, _ = _make_ledger("a", "b")

        assert ledger.mark_soft_dirty("debug_get_node_info") is True
        assert ledger.escalate_to_hard_dirty("stub_link_accepted", step_id="dep-1") is True
        assert ledger.escalate_to_hard_dirty("stub_link_accepted", step_id="dep-2") is False
        assert ledger.causality_mode == CausalityMode.HARD_DIRTY
        assert ledger.causality_break_reason == "stub_link_accepted"
        assert ledger.causality_break_step_id == "dep-1"

        transitions = list(Selector(has_kind=CausalityTransitionRecord).filter(ledger.output_stream))
        assert len(transitions) == 2
        assert transitions[-1].from_mode == CausalityMode.SOFT_DIRTY.value
        assert transitions[-1].to_mode == CausalityMode.HARD_DIRTY.value
        assert transitions[-1].reason == "stub_link_accepted"
        assert transitions[-1].step_id == "dep-1"

    def test_causality_fields_roundtrip_through_structure(self) -> None:
        ledger, _ = _make_ledger("a", "b")
        ledger.mark_soft_dirty("debug_check_expr", step_id="n1")
        ledger.escalate_to_hard_dirty("stub_link_accepted", step_id="dep-5")

        payload = ledger.unstructure()
        restored = Ledger.structure(payload)

        assert restored.causality_mode == CausalityMode.HARD_DIRTY
        assert restored.causality_break_reason == "stub_link_accepted"
        assert restored.causality_break_step_id == "dep-5"


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

    def test_raises_when_call_stack_contains_unresolved_edge_id(self) -> None:
        ledger, _ = _make_ledger("a", "b")
        ledger.call_stack_ids = [uuid4()]
        with pytest.raises(ValueError, match="unresolved edge id"):
            ledger.get_frame()

    def test_make_phase_ctx_includes_populated_local_authorities(self) -> None:
        ledger, _ = _make_ledger("a", "b")
        ledger.local_behaviors.register(
            task="noop",
            func=lambda *, caller=None, ctx=None, **_: None,
        )

        ctx = ledger._make_phase_ctx()

        assert ledger.local_behaviors in ctx.get_authorities()


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

    def test_resolve_choice_forwards_choice_payload_to_frame(self, monkeypatch) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        edge = list(a.edges_out())[0]
        captured: dict[str, object] = {}

        class _FrameWithCapture:
            cursor_steps = 0
            cursor = b
            return_stack = []
            cursor_trace = [b.uid]
            last_redirect = None
            redirect_trace = []

            def resolve_choice(self, arg_edge, *, choice_payload=None, **_kwargs) -> None:
                captured["edge"] = arg_edge
                captured["choice_payload"] = choice_payload

        monkeypatch.setattr(Ledger, "get_frame", lambda self: _FrameWithCapture())
        payload = {"move": "knight", "to": "b6"}
        ledger.resolve_choice(edge.uid, choice_payload=payload)

        assert captured["edge"] is edge
        assert captured["choice_payload"] == payload

    def test_resolve_choice_extends_full_cursor_trace(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        @on_prereqs
        def redirect(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        ledger = Ledger(graph=g, cursor_id=a.uid)
        edge = list(a.edges_out())[0]
        ledger.resolve_choice(edge.uid)

        assert ledger.cursor_history == [a.uid, b.uid, c.uid]
        assert ledger.cursor_id == c.uid
        assert get_visit_count(b.uid, ledger.cursor_history) == 1

    def test_ledger_local_behaviors_participate_in_frame_phase_dispatch(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        b.locals = {}
        edge = list(a.edges_out())[0]

        ledger.local_behaviors.register(
            task="apply_update",
            func=lambda *, caller, ctx, **_: caller.locals.__setitem__("ledger_local", True),
        )

        ledger.resolve_choice(edge.uid)
        assert b.locals["ledger_local"] is True

    def test_resolve_choice_copies_redirect_observability(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)

        @on_prereqs
        def redirect(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        ledger = Ledger(graph=g, cursor_id=a.uid)
        edge = list(a.edges_out())[0]
        ledger.resolve_choice(edge.uid)

        assert ledger.last_redirect is not None
        assert ledger.last_redirect["phase"] == "prereqs"
        assert ledger.last_redirect["successor_id"] == str(c.uid)
        assert len(ledger.redirect_trace) == 1

    def test_container_descent_positions_appear_in_history(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid
        _edge(g, predecessor_id=root.uid, successor_id=container.uid)

        # Register just the container descent prereq handler for this test.
        import tangl.vm.system_handlers as sh
        on_prereqs(sh.descend_into_container)

        ledger = Ledger(graph=g, cursor_id=root.uid)
        edge = list(root.edges_out())[0]
        ledger.resolve_choice(edge.uid)

        assert ledger.cursor_history == [root.uid, container.uid, entry.uid]

    def test_reentrant_steps_increments_on_self_loop_hops(self) -> None:
        ledger, [a, _b] = _make_ledger("a", "b")

        # Drive through ledger path so counters are synchronized from frame trace.
        g = ledger.graph
        edge = _edge(g, predecessor_id=a.uid, successor_id=a.uid)
        before = ledger.reentrant_steps
        ledger.resolve_choice(edge.uid)
        assert ledger.reentrant_steps == before + 1

    def test_resolve_raises_on_missing_edge_and_preserves_state(self) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        initial_choice = ledger.choice_steps
        initial_cursor_steps = ledger.cursor_steps
        initial_cursor_id = ledger.cursor_id
        initial_history = list(ledger.cursor_history)

        with pytest.raises(ValueError, match="Choice edge not found"):
            ledger.resolve_choice(uuid4())

        assert ledger.choice_steps == initial_choice
        assert ledger.cursor_steps == initial_cursor_steps
        assert ledger.cursor_id == initial_cursor_id
        assert ledger.cursor_history == initial_history

    def test_resolve_raises_on_null_return_stack_and_preserves_state(
        self,
        monkeypatch,
    ) -> None:
        ledger, [a, b] = _make_ledger("a", "b")
        edge = list(a.edges_out())[0]
        initial_choice = ledger.choice_steps
        initial_cursor_steps = ledger.cursor_steps
        initial_cursor_id = ledger.cursor_id
        initial_history = list(ledger.cursor_history)

        class _BadFrame:
            cursor_steps = 0
            cursor = a
            return_stack = [None]

            def resolve_choice(self, *_args, **_kwargs) -> None:
                return None

        monkeypatch.setattr(Ledger, "get_frame", lambda self: _BadFrame())

        with pytest.raises(ValueError, match="null edge"):
            ledger.resolve_choice(edge.uid)

        assert ledger.choice_steps == initial_choice
        assert ledger.cursor_steps == initial_cursor_steps
        assert ledger.cursor_id == initial_cursor_id
        assert ledger.cursor_history == initial_history


class TestLedgerJournal:
    def test_get_journal_filters_non_fragments(self) -> None:
        ledger, _ = _make_ledger("a", "b")
        content = ContentFragment(content="hello", step=0)
        choice = ChoiceFragment(text="go", step=1)
        snapshot = Snapshot.from_entity(ledger)
        ledger.output_stream.append(content)
        ledger.output_stream.append(snapshot)
        ledger.output_stream.append(choice)

        journal = ledger.get_journal()
        assert journal == [content, choice]

    def test_get_journal_applies_since_step_and_limit(self) -> None:
        ledger, _ = _make_ledger("a", "b")
        f1 = ContentFragment(content="one", step=0)
        f2 = ContentFragment(content="two", step=2)
        f3 = ChoiceFragment(text="three", step=3)
        ledger.output_stream.extend([f1, f2, f3])

        assert ledger.get_journal(since_step=2) == [f2, f3]
        assert ledger.get_journal(limit=2) == [f2, f3]


class TestLedgerReplayRollback:
    def test_rollback_truncates_and_appends_monument(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(g, predecessor_id=b.uid, successor_id=c.uid)

        ledger = Ledger.from_graph(graph=g, entry_id=a.uid)
        edge_ab = next(a.edges_out())
        edge_bc = next(b.edges_out())
        ledger.resolve_choice(edge_ab.uid)
        ledger.resolve_choice(edge_bc.uid)

        before_count = len(list(ledger.output_stream.values()))
        assert ledger.step == 2
        assert ledger.cursor_id == c.uid

        ledger.rollback_to_step(1, reason="test rollback")

        assert ledger.step == 1
        assert ledger.cursor_id == b.uid
        assert len(list(ledger.output_stream.values())) <= before_count

        monuments = list(Selector(has_kind=RollbackRecord).filter(ledger.output_stream))
        assert len(monuments) == 1
        assert monuments[0].resumed_step == 1
        assert monuments[0].prior_step == 2
        assert monuments[0].truncated_step_count >= 1

        step_records = list(Selector(has_kind=StepRecord).filter(ledger.output_stream))
        assert step_records
        assert all(record.step <= 1 for record in step_records)

    def test_rollback_allows_rebranch_after_truncation(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(g, predecessor_id=b.uid, successor_id=c.uid)

        ledger = Ledger.from_graph(graph=g, entry_id=a.uid)
        edge_ab = next(a.edges_out())
        edge_bc = next(b.edges_out())
        ledger.resolve_choice(edge_ab.uid)
        ledger.resolve_choice(edge_bc.uid)
        ledger.rollback_to_step(1)

        # Re-apply from resumed position.
        ledger.resolve_choice(edge_bc.uid)
        assert ledger.step == 2
        assert ledger.cursor_id == c.uid
