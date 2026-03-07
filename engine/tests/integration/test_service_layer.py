from __future__ import annotations

from typing import Any
from uuid import UUID

from tangl.core import Selector
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service import Orchestrator
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.vm.runtime.ledger import Ledger


class _InMemoryPersistence:
    """Tiny persistence stub that mirrors orchestrator save/get expectations."""

    def __init__(self) -> None:
        self._store: dict[UUID, Any] = {}
        self.saved_payloads: list[Any] = []

    def save(self, payload: Any) -> None:
        key = getattr(payload, "uid", None)
        if key is None and isinstance(payload, dict):
            key = payload.get("uid") or payload.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to infer key for payload")
        self.saved_payloads.append(payload)
        self._store[key] = payload

    def get(self, key: UUID, default: Any | None = None) -> Any:
        return self._store.get(key, default)


def _story38_script() -> dict[str, Any]:
    return {
        "label": "integration_world38",
        "metadata": {
            "title": "Integration Story38",
            "author": "tests",
            "start_at": "intro.start",
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {
                        "content": "End",
                        "media": [{"name": "end.svg", "media_role": "narrative_im"}],
                    },
                },
            },
        },
    }


def _first_choice_edge(ledger: Ledger) -> Action:
    return next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _create_story_session() -> tuple[Orchestrator, _InMemoryPersistence, User, Ledger]:
    persistence = _InMemoryPersistence()
    user = User(label="integration-user")
    persistence.save(user)

    orchestrator = Orchestrator(persistence)
    orchestrator.register_controller(RuntimeController)
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )

    world = World.from_script_data(script_data=_story38_script())
    created = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="integration_story38",
    )

    created_ledger = (created.details or {}).get("ledger")
    assert isinstance(created_ledger, Ledger)
    persisted_ledger = persistence.get(created_ledger.uid)
    assert isinstance(persisted_ledger, Ledger)
    return orchestrator, persistence, user, persisted_ledger


def test_story38_choice_resolution_flow() -> None:
    orchestrator, persistence, user, ledger = _create_story_session()

    old_cursor = ledger.cursor_id
    old_step = ledger.step
    choice = _first_choice_edge(ledger)

    resolved = orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=user.uid,
        choice_id=choice.uid,
    )

    assert resolved.status == "ok"
    updated_ledger = persistence.get(ledger.uid)
    assert isinstance(updated_ledger, Ledger)
    assert updated_ledger.step > old_step
    assert updated_ledger.cursor_id != old_cursor

    update = orchestrator.execute(
        "RuntimeController.get_story_update",
        user_id=user.uid,
        since_step=-1,
    )
    envelope = (update.details or {}).get("envelope")
    assert isinstance(envelope, dict)
    fragments = envelope.get("fragments")
    assert isinstance(fragments, list)
    media_fragments = [
        fragment
        for fragment in fragments
        if isinstance(fragment, dict) and fragment.get("fragment_type") == "media"
    ]
    assert media_fragments


def test_story38_read_endpoint_does_not_persist() -> None:
    orchestrator, persistence, user, _ = _create_story_session()
    saves_before = len(persistence.saved_payloads)

    info = orchestrator.execute(
        "RuntimeController.get_story_update",
        user_id=user.uid,
        since_step=0,
    )

    assert info.status == "ok"
    assert len(persistence.saved_payloads) == saves_before
