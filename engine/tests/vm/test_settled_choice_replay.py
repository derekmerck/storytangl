"""Replay commits graph state at settled choice boundaries."""
from __future__ import annotations

import pytest

from tangl.core import Graph, Node, Selector
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.vm import AnonymousEdge, Ledger, TraversableEdge, TraversableNode
from tangl.vm.replay import Patch, StepRecord
from tangl.vm.provision.provisioner import _next_provision_uid


def test_allocation_sequence_survives_reload_and_does_not_consume_gameplay_rng():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    frame = ledger.get_frame()
    rng_state = frame._random.getstate()
    first = _next_provision_uid(_ctx=frame._make_ctx())
    assert frame._random.getstate() == rng_state
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    second = _next_provision_uid(_ctx=ledger.get_frame()._make_ctx().derive(cursor_id=start.uid))
    assert _next_provision_uid(_ctx=restored.get_frame()._make_ctx()) == second
    assert first != second


def test_failed_submission_preserves_allocation_counter_across_reload():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    target = TraversableNode(label="target", registry=graph)
    edge = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=target.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    allocated = []

    @ledger.local_behaviors.register(task="validate_edge")
    def refuse_after_allocation(*, caller, ctx, **kwargs):
        allocated.append(_next_provision_uid(_ctx=ctx))
        raise ValueError("refused")

    with pytest.raises(ValueError, match="refused"):
        ledger.resolve_choice(edge.uid)
    assert ledger.cursor_id == start.uid and ledger.allocation_counter == 1
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    after_reload = _next_provision_uid(_ctx=restored.get_frame()._make_ctx())
    assert after_reload == _next_provision_uid(_ctx=ledger.get_frame()._make_ctx())
    assert after_reload != allocated[0]


def test_allocation_resets_at_unchanged_settlement_and_rollback():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    middle = TraversableNode(label="middle", registry=graph)
    end = TraversableNode(label="end", registry=graph)
    first = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=middle.uid)
    second = TraversableEdge(registry=graph, predecessor_id=middle.uid, successor_id=end.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    initial_hash = ledger.committed_state_hash
    before = _next_provision_uid(_ctx=ledger.get_frame()._make_ctx())
    ledger.resolve_choice(first.uid)
    assert ledger.committed_state_hash == initial_hash
    assert ledger.allocation_counter == 0 and ledger.allocation_step == 1
    after = _next_provision_uid(_ctx=ledger.get_frame()._make_ctx())
    assert after != before
    ledger.resolve_choice(second.uid)
    ledger.rollback_to_step(1)
    assert ledger.allocation_step == 1 and ledger.allocation_counter == 0
    assert _next_provision_uid(_ctx=ledger.get_frame()._make_ctx()) == after


def test_redirects_share_allocation_boundary_and_leave_gameplay_rng_untouched():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    middle = TraversableNode(label="middle", registry=graph)
    end = TraversableNode(label="end", registry=graph)
    action = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=middle.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    allocations = []

    @ledger.local_behaviors.register(task="apply_update")
    def allocate(*, caller, ctx, **kwargs):
        state = ctx.get_random().getstate()
        allocations.append((ledger.allocation_step, _next_provision_uid(_ctx=ctx)))
        assert ctx.get_random().getstate() == state

    @ledger.local_behaviors.register(task="get_postreqs")
    def redirect(*, caller, ctx, **kwargs):
        if caller is middle:
            return AnonymousEdge(predecessor=middle, successor=end)
        return None

    ledger.resolve_choice(action.uid)
    assert len(allocations) == 2
    assert [step for step, _ in allocations] == [0, 0]
    assert allocations[0][1] != allocations[1][1]
    assert ledger.allocation_step == 2 and ledger.allocation_counter == 0


def test_unchanged_graph_commits_no_delta():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    end = TraversableNode(label="end", registry=graph)
    action = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=end.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(action.uid)
    (record,) = list(Selector(has_kind=StepRecord).filter(ledger.output_stream))
    assert record.settled and record.delta_id is None
    assert record.state_hash == ledger.committed_state_hash
    assert not list(Selector(has_kind=Patch).filter(ledger.output_stream))


def test_loaded_dormant_shape_joins_next_choice_delta_and_replay():
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    middle = TraversableNode(label="middle", registry=graph)
    final = TraversableNode(label="final", registry=graph)
    first = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=middle.uid)
    second = TraversableEdge(registry=graph, predecessor_id=middle.uid, successor_id=final.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.checkpoint_cadence = 100
    seed = ledger.get_frame()._random.getstate()
    dormant = Node(label="dormant", registry=graph)
    assert ledger.get_frame()._random.getstate() == seed
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert restored.get_frame()._random.getstate() == seed
    restored.resolve_choice(first.uid)
    expected_hash = restored.graph.value_hash()
    restored.resolve_choice(second.uid)
    restored.rollback_to_step(1)
    assert restored.graph.value_hash() == expected_hash
    assert restored.graph.get(dormant.uid) is not None


def test_multi_hop_choice_has_one_settled_delta_and_rejects_middle_rollback(monkeypatch):
    graph = Graph()
    start = TraversableNode(label="start", registry=graph)
    middle = TraversableNode(label="middle", registry=graph)
    end = TraversableNode(label="end", registry=graph)
    later = TraversableNode(label="later", registry=graph)
    first = TraversableEdge(registry=graph, predecessor_id=start.uid, successor_id=middle.uid)
    second = TraversableEdge(registry=graph, predecessor_id=end.uid, successor_id=later.uid)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)

    @ledger.local_behaviors.register(task="get_postreqs")
    def redirect(*, caller, ctx, **kwargs):
        if caller is middle:
            return AnonymousEdge(predecessor=middle, successor=end)
        return None

    @ledger.local_behaviors.register(task="apply_update")
    def mark(*, caller, ctx, **kwargs):
        caller.locals["visited"] = True

    original_hash = Graph.value_hash
    live_hashes = []

    def count_hash(self, *args, **kwargs):
        if self is graph:
            live_hashes.append(1)
        return original_hash(self, *args, **kwargs)

    monkeypatch.setattr(Graph, "value_hash", count_hash)
    ledger.resolve_choice(first.uid)
    assert len(live_hashes) == 1
    records = list(Selector(has_kind=StepRecord).filter(ledger.output_stream))
    assert len(records) == 2
    assert not records[0].settled and records[0].delta_id is None
    assert records[1].settled
    assert records[1].delta_id is not None
    assert len(list(Selector(has_kind=Patch).filter(ledger.output_stream))) == 1
    with pytest.raises(ValueError, match="settled choice"):
        ledger.rollback_to_step(1)
    expected = ledger.graph.value_hash()
    ledger.resolve_choice(second.uid)
    ledger.rollback_to_step(2)
    assert ledger.graph.value_hash() == expected
    assert ledger.cursor_id == end.uid
    assert ledger.cursor_history == [start.uid, middle.uid, end.uid]
    assert ledger.current_update_start_step == 1
