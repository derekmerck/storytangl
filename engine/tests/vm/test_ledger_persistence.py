"""Ledger persistence parity checks."""

from __future__ import annotations

from uuid import UUID

from tangl.core import Graph
from tangl.journal.fragments import ChoiceFragment
from tangl.journal.intent import PieceConstraints, PiecesAccepts
from tangl.persistence import PersistenceManager
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.persistence.storage import InMemoryStorage
from tangl.persistence.structuring import StructuringHandler
from tangl.service.user.user import User
from tangl.vm.runtime.ledger import Ledger


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


def test_ledger_round_trip_keeps_a_typed_accepts_choice_in_the_output_stream() -> None:
    """A journalled choice carrying typed ``accepts`` must survive persistence.

    ``unstructure()`` elides defaults, and a union tag is declared as one, so a
    flat dump used to drop it and the restored payload could no longer be
    re-validated against its union -- meaning a ledger whose journal held any
    typed choice could not be reloaded at all (#436).
    """

    graph = Graph()
    start = graph.add_node(label="start")
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    choice = ChoiceFragment(
        edge_id=start.uid,
        text="Inspect a document",
        step=2,
        accepts=PiecesAccepts(
            min=1, max=1, constraints=PieceConstraints(target_zone_ref="packet")
        ),
    )
    ledger.output_stream.append(choice)

    manager = PersistenceManager(
        serializer=JsonSerializationHandler,
        structuring=StructuringHandler,
        storage=InMemoryStorage(),
    )
    manager.save(ledger)
    loaded = manager.get(ledger.uid)

    assert isinstance(loaded, Ledger)
    restored = loaded.output_stream[choice.uid]
    assert isinstance(restored.accepts, PiecesAccepts)
    assert restored.accepts.constraints.target_zone_ref == "packet"
    # The step must survive too: an unstamped choice reads as "still open".
    assert restored.step == 2
