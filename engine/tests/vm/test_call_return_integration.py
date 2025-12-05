"""Integration tests for call/return behavior patterns."""
from __future__ import annotations

from tangl.core import Graph, StreamRegistry
from tangl.story.episode.block import Block
from tangl.vm import Ledger, Frame, ChoiceEdge
from tangl.vm.behaviors import auto_return_from_subgraph
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.resolution_phase import ResolutionPhase as P


def test_simple_call_and_return():
    """A → B call returns to A via POSTREQS behavior."""
    g = Graph(label="simple_call")

    caller = g.add_node(obj_cls=Block, label="caller")
    callee = g.add_node(obj_cls=Block, label="callee")

    call_edge = ChoiceEdge(
        graph=g,
        source_id=caller.uid,
        destination_id=callee.uid,
        is_call=True,
        call_type="test",
        label="Call subroutine",
    )

    @vm_dispatch.register(task=P.POSTREQS, caller=Block)
    def maybe_return(node, *, ctx, **kwargs):
        if node.uid == callee.uid:
            return auto_return_from_subgraph(node, ctx=ctx)
        return None

    try:
        ledger = Ledger(graph=g, cursor_id=caller.uid, records=StreamRegistry())
        ledger.push_snapshot()

        frame = ledger.get_frame()
        frame.resolve_choice(call_edge)

        assert frame.cursor_id == caller.uid
        assert not frame.call_stack
    finally:
        vm_dispatch.remove(maybe_return._behavior)


def test_nested_calls():
    """A → B (call) → C (call) → returns unwind back to A."""
    g = Graph(label="nested")

    a = g.add_node(obj_cls=Block, label="A")
    b = g.add_node(obj_cls=Block, label="B")
    c = g.add_node(obj_cls=Block, label="C")

    ab_call = ChoiceEdge(
        graph=g,
        source_id=a.uid,
        destination_id=b.uid,
        is_call=True,
    )

    bc_call = ChoiceEdge(
        graph=g,
        source_id=b.uid,
        destination_id=c.uid,
        is_call=True,
    )

    @vm_dispatch.register(task=P.POSTREQS, caller=Block)
    def return_from_subgraph(node, *, ctx, **kwargs):
        frame = ctx._frame

        if node.uid == c.uid and frame.call_stack:
            return auto_return_from_subgraph(node, ctx=ctx)

        if node.uid == b.uid and getattr(frame, "_last_returned_to", None) == b.uid:
            frame._last_returned_to = None
            return auto_return_from_subgraph(node, ctx=ctx)
        return None

    try:
        frame = Frame(
            graph=g,
            cursor_id=a.uid,
            call_stack=[],
            cursor_history=[],
        )

        frame.resolve_choice(ab_call)
        frame.resolve_choice(bc_call)

        assert frame.cursor_id == a.uid
        assert not frame.call_stack
    finally:
        vm_dispatch.remove(return_from_subgraph._behavior)


def test_reentry_guard():
    """Caller PREREQS should not re-invoke on return."""
    g = Graph(label="reentry")

    caller = g.add_node(obj_cls=Block, label="caller")
    subroutine = g.add_node(obj_cls=Block, label="subroutine")

    call_count = [0]

    @vm_dispatch.register(task=P.PREREQS, caller=Block)
    def conditional_call(node, *, ctx, **kwargs):
        if node.uid != caller.uid:
            return None

        frame = ctx._frame

        if getattr(frame, "_last_returned_to", None) == caller.uid:
            return None

        call_count[0] += 1
        return ChoiceEdge(
            graph=g,
            source_id=caller.uid,
            destination_id=subroutine.uid,
            is_call=True,
        )

    @vm_dispatch.register(task=P.POSTREQS, caller=Block)
    def return_from_sub(node, *, ctx, **kwargs):
        if node.uid == subroutine.uid:
            return auto_return_from_subgraph(node, ctx=ctx)
        return None

    try:
        frame = Frame(
            graph=g,
            cursor_id=caller.uid,
            call_stack=[],
            cursor_history=[],
        )

        prereq_edge = frame.run_phase(P.PREREQS)
        assert prereq_edge is not None
        assert call_count[0] == 1

        frame.follow_edge(prereq_edge)
        assert frame.cursor_id == caller.uid

        prereq_edge_2 = frame.run_phase(P.PREREQS)
        assert prereq_edge_2 is None
        assert call_count[0] == 1
    finally:
        vm_dispatch.remove(conditional_call._behavior)
        vm_dispatch.remove(return_from_sub._behavior)
