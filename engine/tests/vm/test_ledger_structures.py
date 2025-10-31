import pytest

from tangl.core import Graph, StreamRegistry, Singleton, BehaviorRegistry
from tangl.vm.ledger import Ledger

class SingletonDomain(Singleton, BehaviorRegistry):
    ...

my_test_domain = SingletonDomain(label="my_test_domain")

def test_singleton_domain_structures():

    data = my_test_domain.unstructure()
    print( data )

    # assert Domain.structure(data) is my_test_domain


def _make_minimal_ledger():
    g = Graph()
    start = g.add_node(label="start")
    sr = StreamRegistry()
    ld = Ledger(graph=g, cursor_id=start.uid, step=42, records=sr)
    # ld = Ledger(graph=g, cursor_id=start.uid, step=42, records=sr, domains=[my_test_domain])
    ld.push_snapshot()
    return ld, start


def test_ledger_unstructure_shape():
    """unstructure() returns a dict with graph/domains/records payloads."""
    ld, _ = _make_minimal_ledger()

    data = ld.unstructure()

    assert isinstance(data, dict)
    assert "uid" in data
    assert "obj_cls" in data

    assert "graph" in data
    graph_payload = data["graph"]
    assert isinstance(graph_payload, dict)
    assert "_data" in graph_payload
    assert len(graph_payload["_data"]) >= 1

    # assert "domains" in data
    # assert len(data["domains"]) == 1
    # assert data["domains"][0] == my_test_domain.unstructure()

    assert "records" in data
    records_payload = data["records"]
    assert isinstance(records_payload, dict)
    assert "_data" in records_payload
    assert len(records_payload["_data"]) >= 1


def test_ledger_unstructure_event_sourced_stubs_graph():
    ld, _ = _make_minimal_ledger()
    ld.event_sourced = True

    data = ld.unstructure()

    assert data["graph"] == {"uid": ld.graph.uid, "label": ld.graph.label}

    rebuilt = Ledger.structure(dict(data))
    assert rebuilt.graph.find_one(label="start") is not None


def test_ledger_structure_round_trip():
    """unstructure() → structure() yields an equivalent Ledger:
    cursor, step, graph contents, and record stream contents are preserved."""
    ld, _ = _make_minimal_ledger()
    original_node_labels = {n.label for n in ld.graph.find_nodes()}
    original_record_count = sum(1 for _ in ld.records.find_all())

    # NOTE: structure() pops keys; pass a copy
    data = dict(ld.unstructure())
    rebuilt = Ledger.structure(data)

    # Basic type/identity
    assert isinstance(rebuilt, Ledger)
    assert rebuilt.cursor_id == ld.cursor_id
    assert rebuilt.step == ld.step

    # Graph round-trip: same node labels and count
    rebuilt_labels = {n.label for n in rebuilt.graph.find_nodes()}
    assert rebuilt_labels == original_node_labels
    assert len(list(rebuilt.graph.find_nodes())) == len(original_node_labels)

    # Records round-trip: same count and last snapshot exists
    rebuilt_record_count = sum(1 for _ in rebuilt.records.find_all())
    assert rebuilt_record_count == original_record_count
    assert rebuilt.records.last(channel="snapshot") is not None

    # assert len(rebuilt.domains) == 1 and rebuilt.domains[0] == my_test_domain
