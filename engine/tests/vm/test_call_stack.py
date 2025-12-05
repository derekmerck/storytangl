"""Tests for call stack infrastructure."""

from uuid import uuid4

import pytest

from tangl.core import Graph, StreamRegistry
from tangl.vm import Frame, ChoiceEdge, Ledger
from tangl.vm.frame import StackFrame


def test_stack_frame_construction() -> None:
    """StackFrame can be constructed with required fields."""

    frame = StackFrame(
        return_cursor_id=uuid4(),
        call_site_label="test_caller",
        call_type="test",
        depth=0,
    )

    assert frame.call_site_label == "test_caller"
    assert frame.call_type == "test"
    assert frame.depth == 0


def test_call_edge_pushes_frame() -> None:
    """Following edge with is_call=True pushes a stack frame."""

    g = Graph(label="test")
    caller = g.add_node(label="caller")
    callee = g.add_node(label="callee")

    call_edge = ChoiceEdge(
        graph=g,
        source_id=caller.uid,
        destination_id=callee.uid,
        is_call=True,
        call_type="investigation",
    )

    frame = Frame(graph=g, cursor_id=caller.uid, call_stack=[], cursor_history=[])

    assert len(frame.call_stack) == 0

    frame.follow_edge(call_edge)

    assert len(frame.call_stack) == 1
    assert frame.call_stack[0].return_cursor_id == caller.uid
    assert frame.call_stack[0].call_type == "investigation"
    assert frame.call_stack[0].call_site_label == "caller"


def test_regular_edge_does_not_push_frame() -> None:
    """Following edge with is_call=False doesn't touch stack."""

    g = Graph(label="test")
    a = g.add_node(label="A")
    b = g.add_node(label="B")

    regular_edge = ChoiceEdge(
        graph=g,
        source_id=a.uid,
        destination_id=b.uid,
        is_call=False,
    )

    frame = Frame(graph=g, cursor_id=a.uid, call_stack=[], cursor_history=[])

    frame.follow_edge(regular_edge)

    assert len(frame.call_stack) == 0


def test_nested_calls_push_multiple_frames() -> None:
    """Multiple call edges push multiple frames."""

    g = Graph(label="test")
    a = g.add_node(label="A")
    b = g.add_node(label="B")
    c = g.add_node(label="C")

    ab_call = ChoiceEdge(
        graph=g,
        source_id=a.uid,
        destination_id=b.uid,
        is_call=True,
        call_type="first",
    )

    bc_call = ChoiceEdge(
        graph=g,
        source_id=b.uid,
        destination_id=c.uid,
        is_call=True,
        call_type="second",
    )

    frame = Frame(graph=g, cursor_id=a.uid, call_stack=[], cursor_history=[])

    frame.follow_edge(ab_call)
    assert len(frame.call_stack) == 1
    assert frame.call_stack[0].return_cursor_id == a.uid

    frame.follow_edge(bc_call)
    assert len(frame.call_stack) == 2
    assert frame.call_stack[0].return_cursor_id == a.uid
    assert frame.call_stack[1].return_cursor_id == b.uid


def test_stack_overflow_protection() -> None:
    """50+ nested calls raises RuntimeError."""

    g = Graph(label="overflow")
    nodes = [g.add_node(label=f"node_{i}") for i in range(60)]

    frame = Frame(graph=g, cursor_id=nodes[0].uid, call_stack=[], cursor_history=[])

    for i in range(49):
        edge = ChoiceEdge(
            graph=g,
            source_id=nodes[i].uid,
            destination_id=nodes[i + 1].uid,
            is_call=True,
        )
        frame.follow_edge(edge)

    assert len(frame.call_stack) == 49

    edge_50 = ChoiceEdge(
        graph=g,
        source_id=nodes[49].uid,
        destination_id=nodes[50].uid,
        is_call=True,
    )

    with pytest.raises(RuntimeError, match="Call stack overflow"):
        frame.follow_edge(edge_50)


def test_frame_depth_increments() -> None:
    """Stack frame depth increases with nesting."""

    g = Graph(label="test")
    a = g.add_node(label="A")
    b = g.add_node(label="B")
    c = g.add_node(label="C")

    ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid, is_call=True)
    bc = ChoiceEdge(graph=g, source_id=b.uid, destination_id=c.uid, is_call=True)

    frame = Frame(graph=g, cursor_id=a.uid, call_stack=[], cursor_history=[])

    frame.follow_edge(ab)
    assert frame.call_stack[0].depth == 0

    frame.follow_edge(bc)
    assert frame.call_stack[1].depth == 1


def test_ledger_and_frame_share_call_stack() -> None:
    """Frame mutations to call_stack are visible in Ledger."""

    g = Graph(label="test")
    a = g.add_node(label="A")
    b = g.add_node(label="B")

    call_edge = ChoiceEdge(
        graph=g,
        source_id=a.uid,
        destination_id=b.uid,
        is_call=True,
    )

    ledger = Ledger(
        graph=g,
        cursor_id=a.uid,
        records=StreamRegistry(),
    )

    frame = ledger.get_frame()

    assert frame.call_stack is ledger.call_stack

    frame.follow_edge(call_edge)

    assert len(ledger.call_stack) == 1
