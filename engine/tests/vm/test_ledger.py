from __future__ import annotations

from tangl.core import Graph, Node, StreamRegistry
from tangl.vm.ledger import Ledger
from tangl.vm.replay import Event, EventType, Patch


def test_maybe_push_snapshot_respects_cadence_and_force():
    graph = Graph(label="demo")
    cursor = graph.add_node(label="cursor")
    ledger = Ledger(graph=graph, cursor_id=cursor.uid)
    ledger.records = StreamRegistry()

    ledger.step = 1
    ledger.maybe_push_snapshot(snapshot_cadence=3)
    assert ledger.records.last(channel="snapshot") is None

    ledger.step = 3
    ledger.maybe_push_snapshot(snapshot_cadence=3)
    first_snapshot = ledger.records.last(channel="snapshot")
    assert first_snapshot is not None

    ledger.step = 4
    ledger.maybe_push_snapshot(snapshot_cadence=10)
    assert ledger.records.last(channel="snapshot") is first_snapshot

    ledger.step = 5
    ledger.maybe_push_snapshot(force=True)
    snapshots = list(ledger.records.iter_channel("snapshot"))
    assert len(snapshots) == 2
    assert snapshots[-1].seq >= snapshots[0].seq


def test_recover_graph_from_stream_replays_patches():
    graph = Graph(label="demo")
    cursor = graph.add_node(label="cursor")
    ledger = Ledger(graph=graph, cursor_id=cursor.uid)
    ledger.records = StreamRegistry()

    ledger.step = 0
    ledger.push_snapshot()
    snapshot = ledger.records.last(channel="snapshot")

    created = Node(label="added")
    event = Event(event_type=EventType.CREATE, source_id=graph.uid, value=created)
    patch = Patch(
        registry_id=graph.uid,
        registry_state_hash=snapshot.item_state_hash,
        events=[event],
    )
    ledger.records.add_record(patch)

    recovered = Ledger.recover_graph_from_stream(ledger.records)
    assert recovered.find_one(label="added") is not None
