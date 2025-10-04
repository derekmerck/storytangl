import pytest

from tangl.core import Graph, Node
from tangl.vm.ledger import Ledger
from tangl.vm.replay.patch import Patch
from tangl.vm.replay.watched_proxy import ReplayWatcher, WatchedRegistry

def test_recover_no_snapshot_throws():
    g = Graph(label="demo")
    initial_state_hash = g._state_hash()
    w = ReplayWatcher()
    wg = WatchedRegistry(wrapped=g, watchers=[w])
    n = g.add_node(label="A")  # CREATE event
    pn = wg.get(n.uid)
    pn.label = "B"  # UPDATE event

    # write patch only (no snapshot)
    led = Ledger(graph=g, cursor_id=n.uid)
    led.records.add_record(Patch(events=w.events, registry_id=g.uid, registry_state_hash=initial_state_hash))

    with pytest.raises(RuntimeError):
        g2 = Ledger.recover_graph_from_stream(led.records)

def test_recover_from_snapshot_then_patches():
    g = Graph(label="demo")
    n = g.add_node(label="A")
    led = Ledger(graph=g, cursor_id=n.uid)
    led.push_snapshot()
    initial_state_hash = g._state_hash()
    # mutate original g afterward and capture as a patch
    w = ReplayWatcher(); wg = WatchedRegistry(wrapped=g, watchers=[w])
    pn = wg.get(n.uid); pn.label = "C"
    led.records.add_record(Patch(events=w.events, registry_id=g.uid, registry_state_hash=initial_state_hash))
    g2 = Ledger.recover_graph_from_stream(led.records)
    assert g2.find_one(label="C") is not None


def test_recover_from_snapshot_then_multiple_patches():
    g = Graph(label="demo")
    n = g.add_node(label="A")
    led = Ledger(graph=g, cursor_id=n.uid)
    led.push_snapshot()
    initial_state_hash = g._state_hash()
    # mutate original g afterward and capture as a patch
    w = ReplayWatcher(); wg = WatchedRegistry(wrapped=g, watchers=[w])
    pn = wg.get(n.uid); pn.label = "C"
    led.records.add_record(Patch(events=w.events, registry_id=g.uid, registry_state_hash=initial_state_hash))

    initial_state_hash = g._state_hash()
    w.clear()
    pn.label = "D"
    led.records.add_record(Patch(events=w.events, registry_id=g.uid, registry_state_hash=initial_state_hash))

    g2 = Ledger.recover_graph_from_stream(led.records)
    assert g2.find_one(label="C") is None
    assert g2.find_one(label="D") is not None