"""Canonical ServiceManager contract tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import BaseFragment, Selector
from tangl.journal.fragments import BlockFragment, ChoiceFragment, ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.service.response import (
    CommandEdgeQuery,
    DirectEdgeRequest,
    FindEdgeRequest,
    ProjectedState,
    RuntimeEnvelope,
    RuntimeInfo,
    UserInfo,
    WorldInfo,
)
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


def _story_script(
    *,
    with_choice_payload_hints: bool = False,
    with_choice_blocker: bool = False,
) -> dict[str, object]:
    action: dict[str, object] = {"text": "Continue", "successor": "end"}
    if with_choice_payload_hints:
        action["accepts"] = {
            "kind": "quantity",
            "min": 1,
            "max": 3,
            "unit": "ration",
            "cost_previews": [
                {"ledger_key": "supplies", "delta": -1, "unit": "ration"},
            ],
        }
        action["ui_hints"] = {
            "hotkey": "b",
            "source_kind": "market",
            "contribution": "purchase",
            "cost_previews": [
                {"ledger_key": "purse", "delta": -2, "unit": "coin"},
            ],
        }
    if with_choice_blocker:
        action["conditions"] = ["False"]
        action["blockers"] = [
            {
                "code": "needs_permit",
                "message": "A valid permit is required.",
                "refs": ["permit-status"],
            }
        ]

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
                        "actions": [action],
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

    updated = manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(edge_id=choice.uid),
    )
    assert isinstance(updated, RuntimeEnvelope)
    assert updated.step is not None
    assert updated.step > created.step

    projected = manager.get_story_info(user_id=user.uid)
    assert isinstance(projected, ProjectedState)


def test_find_edge_request_resolves_command_or_returns_transient_guidance(
    manager: ServiceManager,
    user: User,
) -> None:
    world = World.from_script_data(script_data=_story_script())
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_command_flow",
    )

    unknown = manager.resolve_choice(
        user_id=user.uid,
        request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command="dance sideways"),
        ),
    )

    assert unknown.step == created.step
    assert unknown.fragments == []
    assert unknown.ux_events[0].event_type == "edge_not_found"
    assert unknown.ux_events[0].presentation == "inline"
    assert unknown.ux_events[0].replay is False
    assert unknown.metadata["grammar"].examples == ["Continue"]
    assert unknown.metadata["grammar"].verbs[0].verb == "continue"
    assert unknown.metadata["grammar"].verbs[0].frames == ["Continue"]

    resolved = manager.resolve_choice(
        user_id=user.uid,
        request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command="  CONTINUE  "),
        ),
    )

    assert resolved.step > created.step
    assert resolved.ux_events == []


def test_story_envelope_keeps_fragments_independent_from_actions(
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
        story_label="svc_manager_story_fragments",
    )

    assert isinstance(created, RuntimeEnvelope)
    assert not any(isinstance(fragment, BlockFragment) for fragment in created.fragments)
    assert any(isinstance(fragment, ContentFragment) for fragment in created.fragments)

    ledger = persistence[user.current_ledger_id]
    assert isinstance(ledger, Ledger)
    edge = _first_choice_edge(ledger)
    choice = next(fragment for fragment in created.fragments if isinstance(fragment, ChoiceFragment))

    assert choice.uid != edge.uid
    assert choice.edge_id == edge.uid
    assert choice.text == "Continue"
    assert choice.available is True

    payload = choice.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["fragment_type"] == "choice"
    assert payload["uid"] == str(choice.uid)
    assert payload["edge_id"] == str(edge.uid)
    assert payload["uid"] != payload["edge_id"]


def test_story_envelope_preserves_choice_payload_contracts(
    manager: ServiceManager,
    user: User,
) -> None:
    world = World.from_script_data(script_data=_story_script(with_choice_payload_hints=True))
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story_choice_contracts",
    )

    assert isinstance(created, RuntimeEnvelope)
    choice = next(fragment for fragment in created.fragments if isinstance(fragment, ChoiceFragment))
    assert choice.accepts is not None
    assert choice.accepts.kind == "quantity"
    assert choice.ui_hints is not None
    assert choice.ui_hints.hotkey == "b"

    payload = choice.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["accepts"] == {
        "kind": "quantity",
        "required": True,
        "min": 1,
        "max": 3,
        "step": 1,
        "unit": "ration",
        "cost_previews": [
            {"ledger_key": "supplies", "delta": -1, "unit": "ration"},
        ],
    }
    assert payload["ui_hints"] == {
        "hotkey": "b",
        "source_kind": "market",
        "contribution": "purchase",
        "cost_previews": [
            {"ledger_key": "purse", "delta": -2, "unit": "coin"},
        ],
    }
    assert created.metadata["grammar"].examples == ["Continue"]


def test_story_envelope_preserves_typed_choice_blockers(
    manager: ServiceManager,
    user: User,
) -> None:
    world = World.from_script_data(script_data=_story_script(with_choice_blocker=True))
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story_blocker_contract",
    )

    choice = next(fragment for fragment in created.fragments if isinstance(fragment, ChoiceFragment))

    assert choice.available is False
    assert choice.blockers is not None
    assert choice.blockers[0].code == "needs_permit"
    assert choice.blockers[0].message == "A valid permit is required."
    assert choice.blockers[0].refs == ["permit-status"]
    assert choice.model_dump(mode="json", exclude_none=True)["blockers"] == [
        {
            "code": "needs_permit",
            "message": "A valid permit is required.",
            "refs": ["permit-status"],
        }
    ]


def test_create_story_passes_user_namespace_to_world_override(
    manager: ServiceManager,
    persistence,
    user: User,
) -> None:
    class UserScopedWorld(World):
        def _resolve_entry_override(self, graph, namespace):
            if namespace.get("user") is None:
                return None
            target = next(graph.find_nodes(Selector(label="end")), None)
            return getattr(target, "uid", None)

    world = UserScopedWorld.from_script_data(script_data=_story_script())
    manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_story_override",
    )

    ledger = persistence[user.current_ledger_id]
    assert isinstance(ledger, Ledger)
    assert ledger.cursor.label == "end"


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
