from collections.abc import Mapping

import pytest

from tangl.core import Graph
from tangl.core.domain.domain import Domain
from tangl.vm.ledger import Ledger


def _load_ledger(payload):
    if isinstance(payload, Ledger):
        return payload
    if isinstance(payload, Mapping):
        return Ledger.structure(dict(payload))
    raise TypeError(f"Unexpected payload type {type(payload)!r}")


def test_ledger_roundtrip_all_backends(manager):
    graph = Graph()
    node = graph.add_node(label="test_node")
    ledger = Ledger(graph=graph, cursor_id=node.uid, step=42)
    ledger.domains.append(Domain(label="demo_domain"))
    ledger.push_snapshot()

    manager.save(ledger)

    retrieved = manager.get(ledger.uid)
    restored = _load_ledger(retrieved)

    assert restored.uid == ledger.uid
    assert restored.step == 42
    assert restored.cursor_id == node.uid
    assert restored.graph.find_one(label="test_node") is not None
    assert [domain.label for domain in restored.domains] == ["demo_domain"]


def test_event_sourced_rebuild_all_backends(manager):
    graph = Graph()
    node = graph.add_node(label="event_node")
    ledger = Ledger(graph=graph, cursor_id=node.uid, event_sourced=True)
    ledger.push_snapshot()

    manager.save(ledger)

    retrieved = manager.get(ledger.uid)
    restored = _load_ledger(retrieved)

    assert restored.event_sourced is True
    assert restored.graph.find_one(label="event_node") is not None
