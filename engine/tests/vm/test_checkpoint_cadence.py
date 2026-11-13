"""Choice-boundary checkpoint scheduling and constructor-form restoration."""
from __future__ import annotations

import pytest

from tangl.core import Graph, Selector
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.vm import Ledger, TraversableEdge, TraversableNode
from tangl.vm.dispatch import on_prereqs, on_update
from tangl.vm.replay import CheckpointRecord, StepRecord


def _journey() -> tuple[Ledger, list[TraversableEdge]]:
    graph = Graph()
    nodes = [TraversableNode(label=f"node-{i}", registry=graph) for i in range(21)]
    edges = [TraversableEdge(predecessor_id=a.uid, successor_id=b.uid, registry=graph)
             for a, b in zip(nodes, nodes[1:])]
    return Ledger.from_graph(graph, entry_id=nodes[0].uid), edges


def _records(ledger: Ledger, kind: type) -> list:
    return list(Selector(has_kind=kind).filter(ledger.output_stream))


@pytest.mark.parametrize("cadence,expected", [(10, 3), (1, 21)])
def test_cadence_counts_choices_but_retains_every_step(cadence: int, expected: int) -> None:
    ledger, edges = _journey()
    if cadence == 1:
        ledger.checkpoint_cadence = cadence
    else:
        assert ledger.checkpoint_cadence == cadence

    @on_update
    def record_arrival(*, caller, **_kwargs):
        caller.locals["arrived"] = True

    assert [item.step for item in _records(ledger, CheckpointRecord)] == [0]
    for index, edge in enumerate(edges, start=1):
        ledger.resolve_choice(edge.uid)
        if cadence == 10 and index in (9, 10, 19, 20):
            assert len(_records(ledger, CheckpointRecord)) == 1 + index // 10
    assert len(_records(ledger, CheckpointRecord)) == expected
    steps = _records(ledger, StepRecord)
    assert len(steps) == 20
    assert all(step.delta_id is not None for step in steps)


@pytest.mark.parametrize("cadence", [1, 10, 100])
def test_cadence_survives_constructor_and_json_restore(cadence: int) -> None:
    ledger, edges = _journey()
    ledger.checkpoint_cadence = cadence
    for edge in edges[:9]:
        ledger.resolve_choice(edge.uid)
    for data in (ledger.unstructure(), Json.deserialize(Json.serialize(ledger.unstructure()))):
        restored = Ledger.structure(data)
        assert restored.checkpoint_cadence == cadence
        before = len(_records(restored, CheckpointRecord))
        restored.resolve_choice(edges[9].uid)
        assert len(_records(restored, CheckpointRecord)) == before + (cadence in (1, 10))


def test_missing_cadence_uses_declared_class_default() -> None:
    class CustomLedger(Ledger):
        checkpoint_cadence: int = 7

    ledger, _ = _journey()
    assert ledger.checkpoint_cadence == 10
    data = ledger.unstructure()
    del data["checkpoint_cadence"]
    assert Ledger.structure(data).checkpoint_cadence == 10
    assert CustomLedger.structure(data).checkpoint_cadence == 7


def test_forced_snapshot_does_not_shift_periodic_choice_boundary() -> None:
    ledger, edges = _journey()
    for edge in edges[:5]:
        ledger.resolve_choice(edge.uid)
    ledger.save_snapshot(force=True)
    for edge in edges[5:10]:
        ledger.resolve_choice(edge.uid)
    assert [item.step for item in _records(ledger, CheckpointRecord)] == [0, 5, 10]


def test_automatic_hop_is_traced_but_does_not_advance_choice_cadence() -> None:
    graph = Graph()
    nodes = [TraversableNode(label=f"node-{i}", registry=graph) for i in range(12)]
    edges = [TraversableEdge(predecessor_id=a.uid, successor_id=b.uid, registry=graph)
             for a, b in zip(nodes, nodes[1:])]

    @on_prereqs
    def redirect(*, caller, **_kwargs):
        return edges[1] if caller.uid == nodes[1].uid else None

    ledger = Ledger.from_graph(graph, entry_id=nodes[0].uid)
    ledger.resolve_choice(edges[0].uid)
    assert ledger.choice_steps == 1 and ledger.cursor_steps == 2
    assert [record.was_choice for record in _records(ledger, StepRecord)] == [True, False]
    for edge in edges[2:]:
        ledger.resolve_choice(edge.uid)
    assert ledger.choice_steps == 10 and ledger.cursor_steps == 11
    assert [item.step for item in _records(ledger, CheckpointRecord)] == [0, 11]
    assert len(_records(ledger, StepRecord)) == 11
