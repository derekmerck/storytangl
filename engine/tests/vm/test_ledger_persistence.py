"""Ledger persistence parity checks."""

from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import Graph
from tangl.persistence import PersistenceManager
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.persistence.storage import InMemoryStorage
from tangl.persistence.structuring import StructuringHandler
from tangl.service.user.user import User
from tangl.vm.runtime.ledger import Ledger


@pytest.fixture(autouse=True)
def clear_obj_cls_map() -> None:
    PersistenceManager.obj_cls_map.clear()
    yield
    PersistenceManager.obj_cls_map.clear()


def test_ledger38_json_round_trip_keeps_user_id_and_excludes_runtime_user() -> None:
    graph = Graph()
    start = graph.add_node(label="start")
    user = User(label="vm-user")
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    ledger.user = user
    ledger.user_id = user.uid

    manager = PersistenceManager(
        serializer=JsonSerializationHandler,
        structuring=StructuringHandler,
        storage=InMemoryStorage(),
    )
    manager.save(ledger)

    flat = manager.storage[ledger.uid]
    payload = JsonSerializationHandler.deserialize(flat)

    assert payload.get("user_id") == user.uid
    assert "user" not in payload

    loaded = manager.get(ledger.uid)
    assert isinstance(loaded, Ledger)
    assert loaded.user is None
    assert loaded.user_id == user.uid


def test_ledger38_unstructure_remains_uuid_coercible_for_user_id() -> None:
    graph = Graph()
    start = graph.add_node(label="start")
    user = User(label="vm-user")
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    ledger.user = user
    ledger.user_id = user.uid

    payload = ledger.unstructure()

    assert payload.get("user_id") == str(user.uid)
    assert "user" not in payload
    assert UUID(payload["user_id"]) == user.uid
