"""Service38 RuntimeController orchestrator/gateway flow tests.

This is the service38 replacement for the PORT_ADAPT row:
  ``engine/tests/service/controllers/test_runtime_controller.py``
  → ``engine/tests/service38/controllers/test_runtime_controller.py``

The legacy suite focused on direct legacy runtime-controller behavior.
These tests assert the service38-specific contracts:

- ApiEndpoint binding metadata for story38 runtime endpoints.
- Orchestrator hydration and persistence policy behavior for create/do/drop.
- Gateway operation routing for story38 status/update operations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    ResourceBinding,
)
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.gateway import ServiceGateway
from tangl.service.operations import ServiceOperation, endpoint_for_operation
from tangl.service.orchestrator import Orchestrator
from tangl.service.response import RuntimeInfo
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.vm.runtime.ledger import Ledger


class _FakePersistence:
    """Minimal dict-backed persistence for orchestrator tests."""

    def __init__(self) -> None:
        self._store: dict[Any, Any] = {}
        self.saved: list[Any] = []
        self.deleted: list[UUID] = []

    def save(self, payload: Any) -> None:
        key = getattr(payload, "uid", None)
        if key is None and isinstance(payload, dict):
            key = payload.get("uid") or payload.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to determine key for saved payload")
        self.saved.append(payload)
        self._store[key] = payload

    def get(self, key: Any, default: Any = None) -> Any:
        return self._store.get(key, default)

    def remove(self, key: UUID) -> None:
        self.deleted.append(key)
        del self._store[key]

    def __contains__(self, key: Any) -> bool:
        return key in self._store


def _story38_script() -> dict[str, Any]:
    return {
        "label": "svc38_world",
        "metadata": {"title": "Svc 38", "author": "Tests", "start_at": "intro.start"},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {"content": "End"},
                }
            }
        },
    }


def _first_choice_edge(ledger: Ledger) -> Action:
    return next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


@pytest.fixture
def persistence() -> _FakePersistence:
    return _FakePersistence()


@pytest.fixture
def orchestrator(persistence: _FakePersistence) -> Orchestrator:
    orch = Orchestrator(persistence_manager=persistence)
    orch.register_controller(RuntimeController)
    return orch


@pytest.fixture
def gateway(orchestrator: Orchestrator) -> ServiceGateway:
    return ServiceGateway(orchestrator)


@pytest.fixture
def world() -> World:
    return World.from_script_data(script_data=_story38_script())


@pytest.fixture
def existing_user(persistence: _FakePersistence) -> User:
    user = User(label="runtime-user")
    persistence.save(user)
    return user


class TestRuntimeControllerBindingMetadata:
    """ApiEndpoint.binds annotations are correct for each runtime endpoint."""

    def _ep(self, name: str) -> ApiEndpoint:
        endpoint = RuntimeController.get_api_endpoints()[name]
        assert isinstance(endpoint, ApiEndpoint)
        return endpoint

    def test_create_story_binds_user(self) -> None:
        ep = self._ep("create_story")
        assert ep.binds == (ResourceBinding.USER,)
        assert ep.access_level == AccessLevel.PUBLIC

    def test_resolve_choice_binds_ledger(self) -> None:
        ep = self._ep("resolve_choice")
        assert ep.binds == (ResourceBinding.LEDGER,)

    def test_get_story_update_binds_ledger(self) -> None:
        ep = self._ep("get_story_update")
        assert ep.binds == (ResourceBinding.LEDGER,)

    def test_get_story_info_binds_ledger(self) -> None:
        ep = self._ep("get_story_info")
        assert ep.binds == (ResourceBinding.LEDGER,)

    def test_drop_story_binds_user_and_ledger(self) -> None:
        ep = self._ep("drop_story")
        assert ep.binds is not None
        assert ResourceBinding.USER in ep.binds
        assert ResourceBinding.LEDGER in ep.binds


def test_story38_operation_tokens_route_to_registered_runtime_endpoints(
    orchestrator: Orchestrator,
) -> None:
    for operation in (
        ServiceOperation.STORY38_CREATE,
        ServiceOperation.STORY38_UPDATE,
        ServiceOperation.STORY38_DO,
        ServiceOperation.STORY38_STATUS,
        ServiceOperation.STORY38_DROP,
    ):
        endpoint_name = endpoint_for_operation(operation)
        assert endpoint_name in orchestrator._endpoints


def test_create_story_via_orchestrator_persists_ledger_when_policy_set(
    orchestrator: Orchestrator,
    persistence: _FakePersistence,
    world: World,
    existing_user: User,
) -> None:
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )

    result = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=existing_user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story",
    )

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    details = result.details or {}
    ledger = details.get("ledger")
    assert isinstance(ledger, Ledger)
    assert existing_user.current_ledger_id == ledger.uid
    assert ledger.uid in persistence
    assert isinstance(details.get("envelope"), dict)


def test_resolve_choice_via_orchestrator_updates_cursor_and_step(
    orchestrator: Orchestrator,
    persistence: _FakePersistence,
    world: World,
    existing_user: User,
) -> None:
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )
    created = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=existing_user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_choice",
    )
    created_ledger = (created.details or {}).get("ledger")
    assert isinstance(created_ledger, Ledger)

    ledger = persistence.get(created_ledger.uid)
    assert isinstance(ledger, Ledger)
    old_cursor = ledger.cursor_id
    old_step = ledger.step
    choice = _first_choice_edge(ledger)

    resolved = orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=existing_user.uid,
        choice_id=choice.uid,
    )
    assert isinstance(resolved, RuntimeInfo)
    assert resolved.status == "ok"
    details = resolved.details or {}
    envelope = details.get("envelope")
    assert isinstance(envelope, dict)

    persisted_ledger = persistence.get(ledger.uid)
    assert isinstance(persisted_ledger, Ledger)
    assert persisted_ledger.step > old_step
    assert persisted_ledger.cursor_id != old_cursor


def test_gateway_story38_status_and_update_return_runtime_info(
    orchestrator: Orchestrator,
    gateway: ServiceGateway,
    world: World,
    existing_user: User,
) -> None:
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )
    orchestrator.execute(
        "RuntimeController.create_story",
        user_id=existing_user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_gateway",
    )

    info = gateway.execute(ServiceOperation.STORY38_STATUS, user_id=existing_user.uid)
    assert isinstance(info, RuntimeInfo)
    assert info.status == "ok"
    assert info.details is not None

    update = gateway.execute(
        ServiceOperation.STORY38_UPDATE,
        user_id=existing_user.uid,
        since_step=0,
    )
    assert isinstance(update, RuntimeInfo)
    assert update.status == "ok"
    assert update.details is not None
    envelope = update.details.get("envelope")
    assert isinstance(envelope, dict)
    assert isinstance(envelope.get("fragments"), list)



def test_resolve_choice_rejects_legacy_passback_param(
    orchestrator: Orchestrator,
    world: World,
    existing_user: User,
) -> None:
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )
    created = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=existing_user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_payload_only",
    )
    ledger = (created.details or {}).get("ledger")
    assert isinstance(ledger, Ledger)

    choice = _first_choice_edge(ledger)
    with pytest.raises(TypeError, match="passback"):
        orchestrator.execute(
            "RuntimeController.resolve_choice",
            user_id=existing_user.uid,
            choice_id=choice.uid,
            passback={"route": "legacy-client"},
        )


def test_drop_story_via_orchestrator_deletes_ledger_and_unlinks_user(
    orchestrator: Orchestrator,
    persistence: _FakePersistence,
    world: World,
    existing_user: User,
) -> None:
    orchestrator.set_endpoint_policy(
        "RuntimeController.create_story",
        persist_paths=("details.ledger",),
    )
    created = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=existing_user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_drop",
    )
    ledger = (created.details or {}).get("ledger")
    assert isinstance(ledger, Ledger)
    assert ledger.uid in persistence

    dropped = orchestrator.execute("RuntimeController.drop_story", user_id=existing_user.uid, archive=False)
    assert isinstance(dropped, RuntimeInfo)
    assert dropped.status == "ok"
    details = dropped.details or {}
    assert details.get("persistence_deleted") is True
    assert "_delete_ledger_id" not in details
    assert existing_user.current_ledger_id is None
    assert ledger.uid not in persistence
    assert ledger.uid in persistence.deleted
