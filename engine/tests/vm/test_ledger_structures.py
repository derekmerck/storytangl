import pytest

from tangl.core import Graph, StreamRegistry, Domain
from tangl.vm.ledger import Ledger

class SingletonDomain(Domain):
    ...

my_test_domain = SingletonDomain(label="my_test_domain")

def _make_minimal_ledger():
    g = Graph()
    start = g.add_node(label="start")
    sr = StreamRegistry()
    ld = Ledger(graph=g, cursor_id=start.uid, step=42, records=sr, domains=[my_test_domain])
    ld.push_snapshot()
    return ld, start


def test_ledger_unstructure_shape():
    """unstructure() returns a dict with private payloads (_graph/_domains/_records)
    plus the standard Entity fields."""
    ld, _ = _make_minimal_ledger()

    data = ld.unstructure()

    assert isinstance(data, dict)
    # Entity-level metadata
    assert "uid" in data
    assert "obj_cls" in data
    # Ledger private payloads
    assert "_graph" in data
    assert "_domains" in data
    assert len(data["_domains"]) == 1 and data["_domains"][0] == my_test_domain.unstructure()
    assert "_records" in data

    # Graph payload should look like a Registry payload with _data
    gdata = data["_graph"]
    assert isinstance(gdata, dict)
    assert "_data" in gdata
    assert len(gdata["_data"]) >= 1  # at least our 'start' node

    # Records payload should look like a StreamRegistry payload with _data
    rdata = data["_records"]
    assert isinstance(rdata, dict)
    assert "_data" in rdata
    assert len(rdata["_data"]) >= 1  # at least the snapshot we pushed


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

    assert len(rebuilt.domains) == 1 and rebuilt.domains[0] == my_test_domain
