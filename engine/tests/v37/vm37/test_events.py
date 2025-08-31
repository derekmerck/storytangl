import pytest

from tangl.core.graph import Graph, Node
from tangl.vm.events import ReplayWatcher, WatchedRegistry, WatchedEntityProxy, Event


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


def test_events_default_off(session):
    assert not hasattr(session.context.graph, "_watchers")

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

    # now replay on a deepcopy of the original graph
    g2 = Event.replay_all(w.events, g)
    assert g2.find_one(label="ONE") is not None
    assert g2.find_one(label="two") is None
