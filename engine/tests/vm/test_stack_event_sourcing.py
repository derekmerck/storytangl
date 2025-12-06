"""Tests for event-sourced call stack reconstruction."""

from __future__ import annotations

from tangl.core import Graph, StreamRegistry
from tangl.story.episode.block import Block
from tangl.vm import ChoiceEdge, Ledger
from tangl.vm.stack_snapshot import StackFrameSnapshot, StackSnapshot


def test_stack_snapshot_emission() -> None:
    """Stack snapshots are emitted after steps complete."""

    graph = Graph(label="test")
    caller = graph.add_node(obj_cls=Block, label="A")
    callee = graph.add_node(obj_cls=Block, label="B")

    ledger = Ledger(
        graph=graph,
        cursor_id=caller.uid,
        records=StreamRegistry(),
        event_sourced=True,
    )
    ledger.push_snapshot()

    frame = ledger.get_frame()
    call_edge = ChoiceEdge(
        graph=graph,
        source_id=caller.uid,
        destination_id=callee.uid,
        is_call=True,
    )

    frame.follow_edge(call_edge)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    ledger.record_stack_snapshot()

    snapshots = list(ledger.records.find_all(has_channel="stack"))
    assert len(snapshots) == 1
    assert isinstance(snapshots[0], StackSnapshot)
    assert snapshots[0].frames[0].return_cursor_id == caller.uid


def test_stack_reconstruction_to_tail() -> None:
    """Recover the latest stack snapshot."""

    graph = Graph(label="test")
    caller = graph.add_node(obj_cls=Block, label="A")

    records = StreamRegistry()
    records.add_record(
        StackSnapshot(
            frames=[StackFrameSnapshot(return_cursor_id=caller.uid, call_type="flashback")]
        )
    )

    stack = Ledger.recover_stack_from_stream(records, graph)

    assert len(stack) == 1
    assert stack[0].return_cursor_id == caller.uid
    assert stack[0].call_site_label == "A"
    assert stack[0].call_type == "flashback"
    assert stack[0].depth == 0


def test_stack_reconstruction_with_cutoff() -> None:
    """Recover stack state at a specific seq boundary."""

    graph = Graph(label="test")
    caller = graph.add_node(obj_cls=Block, label="A")

    records = StreamRegistry()

    empty_snapshot = StackSnapshot(frames=[])
    records.add_record(empty_snapshot)
    seq_empty = empty_snapshot.seq

    one_call = StackSnapshot(frames=[StackFrameSnapshot(return_cursor_id=caller.uid)])
    records.add_record(one_call)
    seq_one = one_call.seq

    two_calls = StackSnapshot(
        frames=[
            StackFrameSnapshot(return_cursor_id=caller.uid, call_type="first"),
            StackFrameSnapshot(return_cursor_id=caller.uid, call_type="second"),
        ]
    )
    records.add_record(two_calls)

    stack_empty = Ledger.recover_stack_from_stream(records, graph, upto_seq=seq_empty)
    stack_one = Ledger.recover_stack_from_stream(records, graph, upto_seq=seq_one)
    stack_tail = Ledger.recover_stack_from_stream(records, graph)

    assert len(stack_empty) == 0
    assert len(stack_one) == 1
    assert stack_one[0].call_type == "generic"
    assert len(stack_tail) == 2
    assert stack_tail[1].call_type == "second"


def test_event_sourced_structure_uses_stream() -> None:
    """event_sourced ledgers rebuild stacks from the stream."""

    graph = Graph(label="test")
    caller = graph.add_node(obj_cls=Block, label="A")

    ledger = Ledger(
        graph=graph,
        cursor_id=caller.uid,
        records=StreamRegistry(),
        event_sourced=True,
    )
    ledger.push_snapshot()
    ledger.records.add_record(StackSnapshot(frames=[StackFrameSnapshot(return_cursor_id=caller.uid)]))

    data = ledger.unstructure()
    data["call_stack"] = []

    restored = Ledger.structure(data)

    assert len(restored.call_stack) == 1
    assert restored.call_stack[0].return_cursor_id == caller.uid


def test_undo_to_step() -> None:
    """undo_to_step uses snapshots and stack history."""

    graph = Graph(label="undo")
    start = graph.add_node(obj_cls=Block, label="start")
    mid = graph.add_node(obj_cls=Block, label="mid")
    end = graph.add_node(obj_cls=Block, label="end")

    ledger = Ledger(
        graph=graph,
        cursor_id=start.uid,
        records=StreamRegistry(),
        event_sourced=True,
    )
    ledger.push_snapshot()

    frame_first = ledger.get_frame()
    edge_first = ChoiceEdge(
        graph=graph,
        source_id=start.uid,
        destination_id=mid.uid,
        is_call=True,
    )
    frame_first.follow_edge(edge_first)
    ledger.cursor_id = frame_first.cursor_id
    ledger.step = frame_first.step
    ledger.record_stack_snapshot()

    frame_second = ledger.get_frame()
    edge_second = ChoiceEdge(
        graph=graph,
        source_id=mid.uid,
        destination_id=end.uid,
        is_call=True,
        call_type="second",
    )
    frame_second.follow_edge(edge_second)
    ledger.cursor_id = frame_second.cursor_id
    ledger.step = frame_second.step
    ledger.record_stack_snapshot()

    assert ledger.step == 2
    assert ledger.call_stack[-1].return_cursor_id == mid.uid

    ledger.undo_to_step(1)

    assert ledger.step == 1
    assert ledger.call_stack[-1].return_cursor_id == start.uid
