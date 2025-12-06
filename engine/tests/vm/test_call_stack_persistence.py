"""Tests for call stack direct serialization."""

from __future__ import annotations

from tangl.core import Graph, StreamRegistry
from tangl.story.episode.block import Block
from tangl.vm import Ledger, ChoiceEdge
from tangl.vm.behaviors import auto_return_from_subgraph
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.resolution_phase import ResolutionPhase as P


class TestDirectSerialization:
    """Test fast-path serialization for REST interface."""

    def test_call_stack_serializes_with_ledger(self) -> None:
        """Call stack included in ledger.unstructure()."""

        graph = Graph(label="test")
        caller = graph.add_node(obj_cls=Block, label="A")
        callee = graph.add_node(obj_cls=Block, label="B")

        call_edge = ChoiceEdge(
            graph=graph,
            source_id=caller.uid,
            destination_id=callee.uid,
            is_call=True,
            call_type="test_call",
        )

        ledger = Ledger(graph=graph, cursor_id=caller.uid, records=StreamRegistry())
        ledger.push_snapshot()

        frame = ledger.get_frame()
        frame.follow_edge(call_edge)

        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step

        assert len(ledger.call_stack) == 1
        assert ledger.call_stack[0].return_cursor_id == caller.uid

        data = ledger.unstructure()

        assert "call_stack" in data
        assert len(data["call_stack"]) == 1
        assert data["call_stack"][0]["call_type"] == "test_call"

    def test_call_stack_deserializes(self) -> None:
        """structure() restores call stack."""

        graph = Graph(label="test")
        caller = graph.add_node(obj_cls=Block, label="A")
        callee = graph.add_node(obj_cls=Block, label="B")

        ledger = Ledger(graph=graph, cursor_id=caller.uid, records=StreamRegistry())
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

        data = ledger.unstructure()
        restored = Ledger.structure(data)

        assert len(restored.call_stack) == 1
        assert restored.call_stack[0].return_cursor_id == caller.uid

    def test_rest_save_resume_scenario(self) -> None:
        """Simulate REST: save after call, resume, return works."""

        graph = Graph(label="rest")
        caller = graph.add_node(obj_cls=Block, label="caller")
        callee = graph.add_node(obj_cls=Block, label="callee")

        ledger_first = Ledger(graph=graph, cursor_id=caller.uid, records=StreamRegistry())
        ledger_first.push_snapshot()

        frame_first = ledger_first.get_frame()
        call_edge = ChoiceEdge(
            graph=graph,
            source_id=caller.uid,
            destination_id=callee.uid,
            is_call=True,
        )
        frame_first.follow_edge(call_edge)

        ledger_first.cursor_id = frame_first.cursor_id
        ledger_first.step = frame_first.step

        saved_json = ledger_first.unstructure()

        ledger_restored = Ledger.structure(saved_json)

        assert len(ledger_restored.call_stack) == 1
        assert ledger_restored.call_stack[0].return_cursor_id == caller.uid

        @vm_dispatch.register(task=P.POSTREQS, caller=Block)
        def return_handler(node, *, ctx, **kwargs):  # type: ignore[override]
            if node.uid == callee.uid:
                return auto_return_from_subgraph(node, ctx=ctx)
            return None

        try:
            frame_restored = ledger_restored.get_frame()
            frame_restored.run_phase(P.POSTREQS)

            assert frame_restored.cursor_id == caller.uid
            assert len(frame_restored.call_stack) == 0
        finally:
            vm_dispatch.remove(return_handler._behavior)
