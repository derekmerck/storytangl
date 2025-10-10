from tangl.core import Graph
from tangl.persistence import LedgerEnvelope
from tangl.vm.ledger import Ledger
import pytest


def test_ledger_envelope_roundtrip_all_backends(manager):
    graph = Graph()
    node = graph.add_node(label="test_node")
    ledger = Ledger(graph=graph, cursor_id=node.uid, step=42)

    envelope = LedgerEnvelope.from_ledger(ledger)
    manager.save(envelope)

    retrieved = manager.get(ledger.uid)
    restored_envelope = LedgerEnvelope.model_validate(retrieved)
    restored_ledger = restored_envelope.to_ledger()

    assert restored_ledger.uid == ledger.uid
    assert restored_ledger.step == 42
    assert restored_ledger.cursor_id == node.uid
    assert restored_ledger.graph.find_one(label="test_node") is not None


def test_event_sourced_rebuild_all_backends(manager):
    pytest.skip("Event-sourced replay requires snapshot patch hydration; pending upstream fix")
