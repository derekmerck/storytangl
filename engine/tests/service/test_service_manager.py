"""Canonical ServiceManager contract tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import BaseFragment, Selector
from tangl.persistence import PersistenceManagerFactory
from tangl.service.response import ProjectedState, RuntimeEnvelope, RuntimeInfo, UserInfo, WorldInfo
from tangl.service.service_manager import ServiceManager
from tangl.service.service_method import (
    ServiceAccess,
    ServiceContext,
    ServiceWriteback,
)
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.vm.runtime.ledger import Ledger


def _story_script() -> dict[str, object]:
    return {
        "label": "svc_manager_world",
        "metadata": {
            "title": "Service Manager World",
            "author": "Tests",
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
                    },
                },
            },
        },
    }


def _first_choice_edge(ledger: Ledger) -> Action:
    return next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


@pytest.fixture(autouse=True)
def _clear_manual_worlds() -> None:
    from tangl.service.world_registry import clear_manual_worlds, iter_manual_worlds

    snapshot = dict(iter_manual_worlds())
    clear_manual_worlds()
    try:
        yield
    finally:
        clear_manual_worlds()
        for world in snapshot.values():
            from tangl.service.world_registry import register_manual_world

            register_manual_world(world)


@pytest.fixture
def persistence():
    return PersistenceManagerFactory.native_in_mem()


@pytest.fixture
def manager(persistence) -> ServiceManager:
    return ServiceManager(persistence)


@pytest.fixture
def user(persistence) -> User:
    user = User(label="service-manager-user")
    persistence.save(user)
    return user


def test_get_service_methods_exposes_canonical_metadata() -> None:
    methods = ServiceManager.get_service_methods()

    assert methods["create_story"].access is ServiceAccess.CLIENT
    assert methods["create_story"].context is ServiceContext.USER
    assert methods["create_story"].writeback is ServiceWriteback.SESSION
    assert methods["create_story"].operation_id == "story.create"

    assert methods["get_world_media"].capability == "media"
    assert methods["load_world"].capability == "world_mutation"
    assert methods["reset_system"].capability == "dev_tools"


def test_open_session_links_user_and_ledger(manager: ServiceManager, persistence, user: User) -> None:
    world = World.from_script_data(script_data=_story_script())
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story",
    )

    assert isinstance(created, RuntimeEnvelope)
    assert user.current_ledger_id is not None

    with manager.open_session(user_id=user.uid) as session:
        assert session.user is user
        assert session.ledger.uid == user.current_ledger_id
        assert session.ledger.user is user
        assert session.frame.cursor.uid == session.ledger.cursor_id
        assert session.ledger.uid in persistence


def test_story_methods_return_typed_runtime_payloads(
    manager: ServiceManager,
    persistence,
    user: User,
) -> None:
    world = World.from_script_data(script_data=_story_script())
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story_flow",
    )

    assert isinstance(created, RuntimeEnvelope)
    assert created.metadata["world_id"] == world.label
    assert created.metadata["ledger_id"] == str(user.current_ledger_id)
    assert created.fragments
    assert all(isinstance(fragment, BaseFragment) for fragment in created.fragments)

    ledger = persistence[user.current_ledger_id]
    assert isinstance(ledger, Ledger)
    choice = _first_choice_edge(ledger)

    updated = manager.resolve_choice(user_id=user.uid, choice_id=choice.uid)
    assert isinstance(updated, RuntimeEnvelope)
    assert updated.step is not None
    assert updated.step > created.step

    projected = manager.get_story_info(user_id=user.uid)
    assert isinstance(projected, ProjectedState)


def test_story_drop_clears_user_session_without_implicit_ledger_archive(
    manager: ServiceManager,
    persistence,
    user: User,
) -> None:
    world = World.from_script_data(script_data=_story_script())
    manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story_drop",
    )

    ledger_id = user.current_ledger_id
    result = manager.drop_story(user_id=user.uid, archive=True)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert user.current_ledger_id is None
    assert ledger_id is not None
    assert ledger_id in persistence


def test_user_world_and_system_methods_return_typed_models(
    manager: ServiceManager,
    persistence,
) -> None:
    created = manager.create_user(secret="open-sesame", label="typed-user")
    assert isinstance(created, RuntimeInfo)

    created_user_id = UUID(str(created.details["user_id"]))
    info = manager.get_user_info(user_id=created_user_id)
    assert isinstance(info, UserInfo)
    assert info.user_id == created_user_id

    key_info = manager.get_key_for_secret(secret="open-sesame")
    assert key_info.api_key
    assert key_info.user_secret == "open-sesame"

    load_result = manager.load_world(script_data=_story_script())
    assert load_result.status == "ok"
    loaded_world_label = str(load_result.details["world_label"])

    worlds = manager.list_worlds()
    assert worlds
    assert all(isinstance(world, WorldInfo) for world in worlds)

    world_info = manager.get_world_info(world_id=loaded_world_label)
    assert isinstance(world_info, WorldInfo)
    assert world_info.label == loaded_world_label

    system_info = manager.get_system_info()
    assert system_info.engine
