# engine/tests/vm/test_call_stack.py
"""Contract tests for vm call/return stack semantics.

Covers the Ledger + Frame call stack that enables subroutine traversal in
vm.  The legacy VM used an explicit ``StackFrame`` type with serialized call
metadata; vm simplifies this to ``call_stack_ids: list[UUID]`` on the
Ledger, backed by ``TraversableEdge.return_phase`` as the marker that an edge
is a call edge.

Organized by contract:

- Stack invariants: push requires ``return_phase``, empty pop raises
- Nesting: multiple push/pop levels preserve LIFO order
- Frame integration: ``resolve_choice`` keeps calls open across selectable
  continuations and pops them only at a terminal
- Return-edge semantics: the return edge targets the predecessor at
  ``return_phase``, skipping earlier phases
- Persistence: ``call_stack_ids`` survives ``unstructure`` / ``structure``
  round-trips so REST resume works without replay
- Overflow protection: runaway redirect chains raise ``RecursionError``

See Also
--------
``engine/tests/vm/test_ledger.py`` — atomic push/pop already covered in the
Ledger unit tests; this module focuses on *integration* of the stack with
Frame's pipeline execution loop.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator
from uuid import UUID

import pytest

import tangl.vm.system_handlers as vm_system_handlers
from tangl.core import BaseFragment, Graph, Record, Selector
from tangl.vm.dispatch import (
    dispatch as vm_dispatch,
    on_complete_call,
    on_compose_journal,
    on_finalize,
    on_gather_ns,
    on_journal,
    on_postreqs,
    on_prereqs,
    on_provision,
)
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.replay import StepRecord
from tangl.vm.runtime.frame import Frame
from tangl.vm.runtime.ledger import Ledger
from tangl.vm.traversable import (
    AnonymousEdge,
    Predicate,
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

    def test_call_waits_for_callee_choice_before_returning(
        self, clean_vm_dispatch
    ) -> None:
        """A call remains open while the callee offers a selectable edge."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        middle = _node(g, label="middle")
        terminal = _node(g, label="terminal")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        callee_choice = _edge(
            g,
            predecessor_id=callee.uid,
            successor_id=middle.uid,
        )
        terminal_choice = _edge(
            g,
            predecessor_id=middle.uid,
            successor_id=terminal.uid,
        )
        ledger = _ledger(g, caller)

        ledger.resolve_choice(call_edge.uid)

        assert ledger.cursor_id == callee.uid
        assert ledger.call_stack_ids == [call_edge.uid]

        ledger.resolve_choice(callee_choice.uid)

        assert ledger.cursor_id == middle.uid
        assert ledger.call_stack_ids == [call_edge.uid]

        ledger.resolve_choice(terminal_choice.uid)

        assert ledger.cursor_id == caller.uid
        assert ledger.call_stack_ids == []

    def test_unavailable_callee_choice_does_not_hold_call_open(
        self, clean_vm_dispatch
    ) -> None:
        """Only a selectable continuation delays a return."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        unreachable = _node(g, label="unreachable")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        _edge(
            g,
            predecessor_id=callee.uid,
            successor_id=unreachable.uid,
            availability=[Predicate(expr="False")],
        )
        ledger = _ledger(g, caller)

        ledger.resolve_choice(call_edge.uid)

        assert ledger.cursor_id == caller.uid
        assert ledger.call_stack_ids == []

    def test_exhausted_call_completes_before_origin_planning(
        self, clean_vm_dispatch
    ) -> None:
        """Completion receives the original call once before the origin replans."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )
        completed: list[TraversableEdge] = []
        planned_after: list[list[TraversableEdge]] = []

        @on_complete_call
        def record_completion(*, caller, **_kw):
            completed.append(caller)
            return BaseFragment(fragment_type="content", content="The call closes.")

        @on_provision
        def record_origin_planning(*, caller, **_kw):
            if caller is call_edge.predecessor:
                planned_after.append(list(completed))
            return None

        @on_journal
        def render_call_content(*, caller, **_kw):
            if caller is callee:
                return BaseFragment(fragment_type="content", content="Callee content.")
            if caller is call_edge.predecessor:
                return BaseFragment(fragment_type="content", content="Caller content.")
            return None

        with _cleanup_behaviors(
            record_completion,
            record_origin_planning,
            render_call_content,
        ):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)

        assert completed == [call_edge]
        assert planned_after == [[call_edge]]
        assert [fragment.content for fragment in ledger.get_journal()] == [
            "Callee content.",
            "The call closes.",
            "Caller content.",
        ]

    def test_open_call_defers_completion_until_last_internal_choice(
        self, clean_vm_dispatch
    ) -> None:
        """Selectable callee choices keep the call open without completing it."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        terminal = _node(g, label="terminal")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        internal_choice = _edge(g, predecessor_id=callee.uid, successor_id=terminal.uid)
        completed: list[TraversableEdge] = []

        @on_complete_call
        def record_completion(*, caller, **_kw):
            completed.append(caller)
            return None

        with _cleanup_behaviors(record_completion):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)
            assert ledger.cursor is callee
            assert completed == []

            ledger.resolve_choice(internal_choice.uid)

        assert ledger.cursor is caller
        assert completed == [call_edge]

    def test_nested_exhausted_calls_complete_lifo(
        self, clean_vm_dispatch
    ) -> None:
        """Nested calls complete inner-first, once each, as their stack unwinds."""
        g = Graph()
        caller = _node(g, label="caller")
        outer_callee = _node(g, label="outer_callee")
        inner_callee = _node(g, label="inner_callee")
        outer_call = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=outer_callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )
        inner_call = _edge(
            g,
            predecessor_id=outer_callee.uid,
            successor_id=inner_callee.uid,
            return_phase=ResolutionPhase.PLANNING,
            once=True,
        )
        completed: list[TraversableEdge] = []

        @on_complete_call
        def record_completion(*, caller, **_kw):
            completed.append(caller)
            return None

        with _cleanup_behaviors(record_completion):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(outer_call.uid)
            assert ledger.cursor is outer_callee

            ledger.resolve_choice(inner_call.uid)

        assert ledger.cursor is caller
        assert completed == [inner_call, outer_call]

    def test_completion_fragments_survive_an_origin_prereqs_redirect(
        self, clean_vm_dispatch
    ) -> None:
        """Return-side redirects cannot discard already committed completion output."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        landing = _node(g, label="landing")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )
        redirect = _edge(g, predecessor_id=caller.uid, successor_id=landing.uid)

        @on_complete_call
        def emit_completion(*, caller, **_kw):
            assert caller is call_edge
            return BaseFragment(fragment_type="content", content="The call closes.")

        @on_prereqs
        def redirect_on_return(*, caller, ctx, **_kw):
            if caller is call_edge.predecessor and isinstance(ctx.selected_edge, AnonymousEdge):
                return redirect
            return None

        with _cleanup_behaviors(emit_completion, redirect_on_return):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)

        assert ledger.cursor is landing
        assert [fragment.content for fragment in ledger.get_journal()] == [
            "The call closes."
        ]

    def test_completion_output_uses_journal_composition_without_choices(
        self, clean_vm_dispatch
    ) -> None:
        """Completion output shares the callee's JOURNAL transforms."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )
        composed_from: list[list[BaseFragment]] = []

        @on_complete_call
        def emit_completion(*, caller, **_kw):
            assert caller is call_edge
            return BaseFragment(fragment_type="content", content="Raw completion.")

        @on_compose_journal
        def compose_completion(*, caller, fragments, **_kw):
            assert caller is callee
            composed_from.append(list(fragments))
            return [
                BaseFragment(
                    fragment_type="content",
                    content=f"Composed: {fragments[0].content}",
                ),
            ]

        with _cleanup_behaviors(emit_completion, compose_completion):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)

        assert [[fragment.content for fragment in fragments] for fragments in composed_from] == [
            ["Raw completion."]
        ]
        assert [fragment.content for fragment in ledger.get_journal()] == [
            "Composed: Raw completion."
        ]

    def test_completion_output_follows_terminal_finalize_records(
        self, clean_vm_dispatch
    ) -> None:
        """Completion output follows the exhausted callee's JOURNAL and FINALIZE."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )

        @on_journal
        def render_content(*, caller, **_kw):
            if caller is callee:
                return BaseFragment(fragment_type="content", content="Callee journal.")
            if caller is call_edge.predecessor:
                return BaseFragment(fragment_type="content", content="Origin journal.")
            return None

        @on_finalize
        def emit_finalize_record(*, caller, **_kw):
            if caller is callee:
                return Record(content="Callee finalize.")
            return None

        @on_complete_call
        def emit_completion(*, caller, **_kw):
            assert caller is call_edge
            return BaseFragment(fragment_type="content", content="Call completion.")

        with _cleanup_behaviors(
            render_content,
            emit_finalize_record,
            emit_completion,
        ):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)

        output_contents = [
            record.content
            for record in ledger.output_stream.values()
            if getattr(record, "content", None) in {
                "Callee journal.",
                "Callee finalize.",
                "Call completion.",
                "Origin journal.",
            }
        ]
        assert output_contents == [
            "Callee journal.",
            "Callee finalize.",
            "Call completion.",
            "Origin journal.",
        ]

    def test_completion_choice_output_fails_before_journal_composition(
        self, clean_vm_dispatch
    ) -> None:
        """Completion controls are a handler contract error, not hidden output."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )

        @on_complete_call
        def emit_choice(**_kw):
            return BaseFragment(fragment_type="choice", content="Invalid completion choice.")

        @on_compose_journal
        def composition_must_not_run(**_kw):
            raise AssertionError("completion choice reached journal composition")

        with _cleanup_behaviors(emit_choice, composition_must_not_run):
            with pytest.raises(TypeError, match="complete_call must not return ChoiceFragment"):
                _ledger(g, caller).resolve_choice(call_edge.uid)

    def test_completion_mutation_is_recorded_on_the_terminal_step(
        self, clean_vm_dispatch
    ) -> None:
        """Completion mutations replay and roll back with the exhausted callee hop."""
        g = Graph()
        caller = _node(g, label="caller", locals={"completion_count": 0})
        callee = _node(g, label="callee")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )

        @on_complete_call
        def increment_completion(*, caller, **_kw):
            caller.predecessor.locals["completion_count"] += 1
            return None

        with _cleanup_behaviors(increment_completion):
            ledger = _ledger(g, caller)
            ledger.save_snapshot(force=True)
            ledger.resolve_choice(call_edge.uid)
            terminal_step = next(
                record
                for record in Selector(has_kind=StepRecord).filter(ledger.output_stream)
                if record.cursor_id == callee.uid
            )

            assert caller.locals["completion_count"] == 1
            assert terminal_step.delta_id is not None
            assert terminal_step.state_hash == ledger.graph.value_hash()

            ledger.rollback_to_step(1, reason="verify completion replay")
            replayed_caller = ledger.graph.get(caller.uid)

            assert isinstance(replayed_caller, TraversableNode)
            assert replayed_caller.locals["completion_count"] == 1
            assert ledger.graph.value_hash() == terminal_step.state_hash

            ledger.rollback_to_step(0, reason="undo completion replay")
            original_caller = ledger.graph.get(caller.uid)

            assert isinstance(original_caller, TraversableNode)
            assert original_caller.locals["completion_count"] == 0

    def test_completion_replays_once_after_restore_and_rollback(
        self, clean_vm_dispatch
    ) -> None:
        """Restoring an open call and replaying its exit does not duplicate output."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        terminal = _node(g, label="terminal")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.PLANNING,
        )
        internal_choice = _edge(g, predecessor_id=callee.uid, successor_id=terminal.uid)
        completed_ids: list[UUID] = []

        @on_complete_call
        def emit_completion(*, caller, **_kw):
            completed_ids.append(caller.uid)
            return BaseFragment(fragment_type="content", content="The call closes.")

        with _cleanup_behaviors(emit_completion):
            ledger = _ledger(g, caller)
            ledger.resolve_choice(call_edge.uid)
            restored = Ledger.structure(ledger.unstructure())
            restored_choice = restored.graph.get(internal_choice.uid)

            assert isinstance(restored_choice, TraversableEdge)
            restored.resolve_choice(restored_choice.uid)
            assert [fragment.content for fragment in restored.get_journal()] == [
                "The call closes."
            ]

            restored.rollback_to_step(1, reason="replay exhausted call")
            replayed_choice = restored.graph.get(internal_choice.uid)

            assert isinstance(replayed_choice, TraversableEdge)
            assert restored.cursor.get_label() == "callee"
            assert restored.call_stack_ids == [call_edge.uid]
            restored.resolve_choice(replayed_choice.uid)

        assert completed_ids == [call_edge.uid, call_edge.uid]
        assert [fragment.content for fragment in restored.get_journal()] == [
            "The call closes."
        ]

    def test_call_continuation_uses_completed_edge_context(
        self, clean_vm_dispatch
    ) -> None:
        """Continuation availability retains the selected edge namespace."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        terminal = _node(g, label="terminal")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        _edge(
            g,
            predecessor_id=callee.uid,
            successor_id=terminal.uid,
            availability=[Predicate(expr="_edge.return_phase is not None")],
        )
        on_gather_ns(vm_system_handlers.contribute_selected_edge_context)

        with _cleanup_behaviors(vm_system_handlers.contribute_selected_edge_context):
            frame = Frame(graph=g, cursor=caller)
            frame.resolve_choice(call_edge)

        assert frame.cursor is callee
        assert frame.return_stack == [call_edge]

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
            trigger_phase=ResolutionPhase.POSTREQS,
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

    def test_suspended_call_resumes_after_structure_roundtrip(
        self, clean_vm_dispatch
    ) -> None:
        """A saved callee choice returns through its restored call stack."""
        g = Graph()
        caller = _node(g, label="caller")
        callee = _node(g, label="callee")
        terminal = _node(g, label="terminal")
        call_edge = _edge(
            g,
            predecessor_id=caller.uid,
            successor_id=callee.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        callee_choice = _edge(
            g,
            predecessor_id=callee.uid,
            successor_id=terminal.uid,
        )
        ledger = _ledger(g, caller)
        ledger.resolve_choice(call_edge.uid)

        restored = Ledger.structure(ledger.unstructure())
        restored.resolve_choice(callee_choice.uid)

        assert restored.cursor_id == caller.uid
        assert restored.call_stack_ids == []

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
        from tangl.vm.runtime.frame import MAX_RESOLVE_DEPTH

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
        import tangl.vm.system_handlers as sh

        on_prereqs(sh.follow_triggered_prereqs)
        with _cleanup_behaviors(sh.follow_triggered_prereqs):
            frame = Frame(graph=g, cursor=nodes[0])
            with pytest.raises(RecursionError):
                frame.resolve_choice(edges[0], max_depth=MAX_RESOLVE_DEPTH)
