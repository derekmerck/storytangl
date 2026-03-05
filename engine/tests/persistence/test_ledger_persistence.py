from collections.abc import Mapping

import pytest

from tangl.core38 import Graph
# from tangl.core.domain.affiliate import SingletonDomain
from tangl.vm38 import Ledger
from tangl.vm38.replay import CheckpointRecord


def _load_ledger(payload):
    if isinstance(payload, Ledger):
        return payload
    if isinstance(payload, Mapping):
        return Ledger.structure(dict(payload))
    raise TypeError(f"Unexpected payload type {type(payload)!r}")

# @pytest.fixture(autouse=True)
# def clear_singleton_domain():
#     SingletonDomain.clear_instances()
#     yield
#     SingletonDomain.clear_instances()
#

def test_ledger_roundtrip_all_backends(manager):
    graph = Graph()
    node = graph.add_node(label="test_node")
    ledger = Ledger(graph=graph, cursor_id=node.uid, cursor_steps=42)
    # ledger.domains.append(SingletonDomain(label="demo_domain"))
    ledger.push_snapshot()

    manager.save(ledger)

    retrieved = manager.get(ledger.uid)
    restored = _load_ledger(retrieved)

    assert restored.uid == ledger.uid
    assert restored.step == 42
    assert restored.cursor_id == node.uid
    assert restored.graph.find_one(label="test_node") is not None
    # assert [domain.label for domain in restored.domains] == ["demo_domain"]


def test_event_sourced_rebuild_all_backends(manager):
    graph = Graph()
    node = graph.add_node(label="event_node")
    ledger = Ledger(graph=graph, cursor_id=node.uid)
    ledger.push_snapshot()

    manager.save(ledger)

    retrieved = manager.get(ledger.uid)
    restored = _load_ledger(retrieved)

    assert restored.records.last(is_instance=CheckpointRecord) is not None
    assert restored.graph.find_one(label="event_node") is not None
