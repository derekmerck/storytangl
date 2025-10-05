import pytest

from tangl.core import StreamRegistry, Record, Graph, Node
from tangl.vm.replay.events import Event, EventType
from tangl.vm.replay.patch import Patch, Snapshot
from tangl.vm.replay.watched_proxy import ReplayWatcher, WatchedRegistry
from tangl.vm.ledger import Ledger

# ---------- Ledger restore ----------

def _mk_patch_create_node(registry_id, node_dict):
    ev = Event(source_id=registry_id, event_type=EventType.CREATE, name=None, value=node_dict)
    p = Patch(events=[ev], registry_id=registry_id)
    return p

def test_restore_with_snapshot_and_patches():
    g0 = Graph()
    a = g0.add_node(label="A")
    sr = StreamRegistry()

    # Snapshot
    snap = Snapshot.from_item(g0)
    sr.add_record(snap)

    # Patch creating B
    b = Node(label="B")
    p = _mk_patch_create_node(g0.uid, b.unstructure())
    sr.add_record(p)

    g1 = Ledger.recover_graph_from_stream(sr)
    assert any(n.get_label()=="A" for n in g1.find_nodes())
    assert any(n.get_label()=="B" for n in g1.find_nodes())

def test_restore_without_snapshot_behavior_is_explicit():
    sr = StreamRegistry()
    with pytest.raises(RuntimeError):
        g = Ledger.recover_graph_from_stream(sr)

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