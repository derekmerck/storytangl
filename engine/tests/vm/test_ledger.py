from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import Graph, StreamRegistry, Snapshot
from tangl.vm import ChoiceEdge, ResolutionPhase, Ledger
from tangl.vm.replay import Event, EventType, Patch


def test_init_cursor_generates_journal_entry() -> None:
    graph = Graph(label="test")
    start = graph.add_node(label="start")

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    assert ledger.step == 0
    from tangl.core.record import BaseFragment
    assert list(ledger.records.find_all(is_instance=BaseFragment)) == []

    ledger.init_cursor()

    assert ledger.step >= 1
    fragments = list(ledger.records.find_all(is_instance=BaseFragment))
    assert fragments


def test_init_cursor_follows_prereq_redirects() -> None:
    graph = Graph(label="test")
    start = graph.add_node(label="start")
    forced = graph.add_node(label="forced_destination")

    ChoiceEdge(
        graph=graph,
        source_id=start.uid,
        destination_id=forced.uid,
        trigger_phase=ResolutionPhase.PREREQS,
    )

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    ledger.init_cursor()

    assert ledger.cursor_id == forced.uid
    assert ledger.step >= 1


def test_init_cursor_with_invalid_cursor_raises() -> None:
    graph = Graph(label="test")
    ledger = Ledger(graph=graph, cursor_id=uuid4(), records=StreamRegistry())

    with pytest.raises(RuntimeError, match="not found in graph"):
        ledger.init_cursor()


def test_maybe_push_snapshot_respects_cadence() -> None:
    graph = Graph(label="cadence")
    start = graph.add_node(label="start")
    ledger = Ledger(
        graph=graph,
        cursor_id=start.uid,
        records=StreamRegistry(),
        snapshot_cadence=3,
    )

    # No snapshot until step divisible by cadence unless forced.
    ledger.step = 1
    ledger.maybe_push_snapshot()
    assert list(ledger.records.find_all(is_instance=Snapshot)) == []

    ledger.step = 2
    ledger.maybe_push_snapshot()
    assert list(ledger.records.find_all(is_instance=Snapshot)) == []

    ledger.step = 3
    ledger.maybe_push_snapshot()
    snapshots = list(ledger.records.find_all(is_instance=Snapshot))
    assert len(snapshots) == 1

    ledger.step = 4
    ledger.maybe_push_snapshot(force=True)
    snapshots = list(ledger.records.find_all(is_instance=Snapshot))
    assert len(snapshots) == 2


def test_recover_graph_from_stream_round_trip() -> None:
    graph = Graph(label="round-trip")
    start = graph.add_node(label="start")

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    baseline_hash = ledger.graph._state_hash()
    update_event = Event(
        event_type=EventType.UPDATE,
        source_id=start.uid,
        name="label",
        value="updated",
    )
    patch = Patch(
        events=[update_event],
        registry_id=ledger.graph.uid,
        registry_state_hash=baseline_hash,
    )
    ledger.records.add_record(patch)

    # Simulate live graph mutation to match the patch.
    start.label = "updated"

    recovered_graph = Ledger.recover_graph_from_stream(ledger.records)

    def project(g: Graph) -> dict[str, list[tuple]]:
        nodes = sorted((node.uid, node.label) for node in g.find_nodes())
        edges = sorted(
            (
                edge.uid,
                edge.source_id,
                edge.destination_id,
                getattr(edge, "edge_type", None),
            )
            for edge in g.find_edges()
        )
        return {"nodes": nodes, "edges": edges}

    assert project(recovered_graph) == project(ledger.graph)
