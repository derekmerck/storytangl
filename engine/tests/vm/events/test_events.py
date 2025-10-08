import pytest

from tangl.core.graph import Graph, Node
from tangl.vm.replay import ReplayWatcher, WatchedRegistry, WatchedEntityProxy, EventType, Patch


def test_proxy_sets_wrapped_and_emits(graph):
    g = graph
    n = g.add_node(label="X")
    rw = ReplayWatcher()
    proxy = WatchedEntityProxy(n, [rw])
    proxy.label = "Y"
    assert n.label == "Y"
    assert rw.events[-1].event_type.name == "UPDATE"
    assert rw.events[-1].name == "label"
    assert rw.events[-1].value == "Y"
    assert rw.events[-1].old_value == "X"


def test_events_default_off(frame):
    assert not hasattr(frame.context.graph, "_watchers")

@pytest.mark.xfail(reason="removed this func for mvp")
def test_preview_graph_is_copy(session):
    s = session
    _ = s.get_context()  # creates watched proxy
    # mutate via proxy -> event recorded
    s.context.graph.add_node(label="A")
    # preview shows mutation
    g_prev = s.get_preview_graph()
    assert any(n.label == "A" for n in g_prev.nodes())
    # original graph unchanged
    assert not any(n.label == "A" for n in s.graph.nodes())


def test_event_replay_create_update_delete_roundtrip():
    g = Graph()
    n = g.add_node(label="one")
    w = ReplayWatcher()

    wg = WatchedRegistry(wrapped=g, watchers=[w])

    # CREATE: add a node
    n2 = Node(label="two")
    wg.add(n2)

    # UPDATE: change label on wrapped node through proxy.get()
    pn1 = wg.get(n.uid)
    pn1.label = "ONE"

    # DELETE: remove node by uid
    wg.remove(n2.uid)

    p = Patch(events=w.events)

    # now replay on a deepcopy of the original graph
    g2 = p.apply(g)
    assert g2.find_one(label="ONE") is not None
    assert g2.find_one(label="two") is None


def test_event_replay_is_idempotent():
    g = Graph()
    n = g.add_node(label="X")
    w = ReplayWatcher()
    wg = WatchedRegistry(wrapped=g, watchers=[w])

    # mutate twice
    pn = wg.get(n.uid)
    pn.label = "Y"
    pn.label = "Z"

    p = Patch(events=w.events)

    # apply twice to fresh clones; results should match
    g1 = p.apply(g)
    g2 = p.apply(g)
    assert g1.find_one(label="Z") and g2.find_one(label="Z")

def test_proxy_nested_attribute_update_records():
    # When a Node has a dict-like locals, ensure nested set emits UPDATE
    g = Graph()
    n = g.add_node(label="N")
    n.__dict__['locals'] = {}
    w = ReplayWatcher()
    p = WatchedEntityProxy(n, [w])

    p.locals["color"] = "red"  # __setitem__ path
    assert w.events[-1].event_type.name == "UPDATE"
    assert w.events[-1].name == "locals"
    assert w.events[-1].value == {"color": "red"}


def test_patch_state_hash_mismatch_raises():
    g = Graph(label="demo"); n = g.add_node(label="A")
    # wrong baseline hash
    bad_hash = b'\x00'*32
    w = ReplayWatcher(); wg = WatchedRegistry(wrapped=g, watchers=[w]); wg.get(n.uid).label = "B"

    # Can apply with correct hash
    p = Patch(events=w.events, registry_id=g.uid, registry_state_hash=g._state_hash())
    p.apply(g)

    # Raises with incorrect hash
    pb = Patch(events=w.events, registry_id=g.uid, registry_state_hash=bad_hash)
    with pytest.raises(ValueError):
        pb.apply(g)

def test_entity_proxy_nested_collection_emits_top_level_update(graph):
    g = graph
    n = g.add_node(label="X")
    n.__dict__["locals"] = {"a": {"b": 0}}
    w = ReplayWatcher()
    p = WatchedEntityProxy(n, [w])
    p.locals["a"]["b"] = 1
    assert w.events[-1].event_type == EventType.UPDATE  # adjust if attribute name
    assert w.events[-1].name == "locals"
    assert w.events[-1].value == {"a": {"b": 1}}