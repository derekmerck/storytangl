from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from unittest.mock import Mock

from tangl.core import BaseFragment, Graph, StreamRegistry
from tangl.journal.content import ContentFragment
from tangl.service import Orchestrator
from tangl.service.controllers import RuntimeController
from tangl.vm import ChoiceEdge, ResolutionPhase, Ledger


@dataclass
class _StubUser:
    uid: UUID
    current_ledger_id: UUID


class _InMemoryPersistence(dict[UUID, Any]):
    """Tiny persistence stub that mimics the orchestration expectations."""

    def __init__(self) -> None:
        super().__init__()
        self.saved_payloads: list[Any] = []

    def get(self, key: UUID, default: Any | None = None) -> Any:  # pragma: no cover - Mapping compatibility
        return super().get(key, default)

    def save(self, payload: Any) -> None:
        self.saved_payloads.append(payload)
        key = getattr(payload, "uid", None)
        if key is None and isinstance(payload, dict):
            key = payload.get("uid") or payload.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to infer key for payload")
        self[key] = payload


class _ReadOnlyPersistence:
    """Minimal mapping that mimics :class:`~tangl.persistence.PersistenceManager`."""

    def __init__(self, user: _StubUser, ledger_payload: Any) -> None:
        self._store: dict[UUID, Any] = {user.uid: user}
        if hasattr(ledger_payload, "uid"):
            self._store[ledger_payload.uid] = ledger_payload
        elif isinstance(ledger_payload, dict):
            self._store[ledger_payload.get("uid")] = ledger_payload
        else:
            raise TypeError("Unsupported ledger payload for read-only persistence")
        self.save = Mock()

    def __getitem__(self, key: UUID) -> Any:
        return self._store[key]


def _build_ledger_with_choice() -> tuple[Ledger, UUID]:
    graph = Graph(label="integration")
    start = graph.add_node(label="start")
    end = graph.add_node(label="end")
    choice = ChoiceEdge(graph=graph, source_id=start.uid, destination_id=end.uid, label="go")
    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    frame = ledger.get_frame()

    @frame.local_behaviors.register(task=ResolutionPhase.JOURNAL)
    def _journal_handler(*_: Any, ctx: SimpleNamespace, **__: Any) -> list[ContentFragment]:
        return [ContentFragment(content=f"cursor:{ctx.cursor.label}")]

    frame._invalidate_context()
    return ledger, choice.uid


def test_full_choice_resolution_flow() -> None:
    persistence = _InMemoryPersistence()
    ledger, choice_id = _build_ledger_with_choice()
    user = _StubUser(uid=uuid4(), current_ledger_id=ledger.uid)

    persistence[user.uid] = user
    persistence[ledger.uid] = ledger

    orchestrator = Orchestrator(persistence)
    orchestrator.register_controller(RuntimeController)

    initial_cursor = ledger.cursor_id
    baseline_seq = ledger.records.max_seq

    result = orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=user.uid,
        choice_id=choice_id,
    )

    assert result.cursor_id != initial_cursor
    assert result.status == "ok"

    saved_payload = persistence.saved_payloads[-1]
    if isinstance(saved_payload, Ledger):
        saved_ledger = saved_payload
    elif isinstance(saved_payload, dict):
        saved_ledger = Ledger.structure(dict(saved_payload))
    else:
        raise TypeError(f"Unexpected payload type {type(saved_payload)!r}")

    assert saved_ledger.uid == ledger.uid
    assert saved_ledger.records.max_seq > baseline_seq

    fragments = orchestrator.execute(
        "RuntimeController.get_journal_entries",
        user_id=user.uid,
        limit=0,
    )
    assert fragments, "journal fragments should be available via get_journal_entries"
    for fragment in fragments:
        assert isinstance(fragment, BaseFragment)


def test_read_only_endpoint_does_not_persist() -> None:
    ledger, _ = _build_ledger_with_choice()
    user = _StubUser(uid=uuid4(), current_ledger_id=ledger.uid)
    ledger_payload = ledger.unstructure()

    persistence = _ReadOnlyPersistence(user, ledger_payload)

    orchestrator = Orchestrator(persistence)
    orchestrator.register_controller(RuntimeController)

    orchestrator.execute("RuntimeController.get_journal_entries", user_id=user.uid)

    persistence.save.assert_not_called()
