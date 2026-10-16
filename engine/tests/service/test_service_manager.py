"""Canonical ServiceManager contract tests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest
from jinja2 import UndefinedError

from tangl.core import BaseFragment, Selector
from tangl.journal.fragments import BlockFragment, ChoiceFragment, ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.presentation.projection import (
    BrandingValue,
    ProjectedState,
    StageExtentValue,
    TableValue,
)
from tangl.service.response import (
    CommandEdgeQuery,
    DirectEdgeRequest,
    FindEdgeRequest,
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
from tangl.story import InitMode, MenuBlock, World
from tangl.story.episode import Action
from tangl.vm.runtime.ledger import Ledger


def _story_script(
    *,
    with_choice_payload_hints: bool = False,
    with_choice_blocker: bool = False,
    with_call: bool = False,
    stage_extent: dict[str, object] | None = None,
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

    metadata: dict[str, object] = {
        "title": "Service Manager World",
        "author": "Tests",
        "start_at": "intro.start",
    }
    if stage_extent is not None:
        metadata["stage_extent"] = stage_extent

    blocks: dict[str, object] = {
        "start": {
            "content": "Start",
            "actions": [action],
        },
        "end": {
            "content": "End",
        },
    }
    if with_call:
        blocks = {
            "start": {
                "content": "Start",
                "actions": [
                    {"text": "Get help", "successor": "clinic", "return": True},
                    {"text": "Leave", "successor": "end"},
                ],
            },
            "clinic": {
                "content": "Clinic",
                "actions": [{"text": "Continue treatment", "successor": "end"}],
            },
            "end": {"content": "End"},
        }

    return {
        "label": "svc_manager_world",
        "metadata": metadata,
        "scenes": {
            "intro": {
                "blocks": {
                    **blocks,
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


def test_service_resolves_a_suspended_call_through_the_callee_choice(
    manager: ServiceManager,
    persistence,
    user: User,
) -> None:
    """The client receives and can submit a choice from a called block."""
    world = World.from_script_data(script_data=_story_script(with_call=True))
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc_manager_call_flow",
    )
    call_choice = next(
        fragment
        for fragment in created.fragments
        if isinstance(fragment, ChoiceFragment) and fragment.text == "Get help"
    )

    suspended = manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(edge_id=call_choice.edge_id),
    )

    callee_choice = next(
        fragment
        for fragment in suspended.fragments
        if isinstance(fragment, ChoiceFragment) and fragment.text == "Continue treatment"
    )
    ledger = persistence[user.current_ledger_id]
    assert ledger.cursor.label == "clinic"
    assert len(ledger.call_stack_ids) == 1

    returned = manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(edge_id=callee_choice.edge_id),
    )

    assert {fragment.text for fragment in returned.fragments if isinstance(fragment, ChoiceFragment)} == {
        "Get help",
        "Leave",
    }
    assert ledger.cursor.label == "start"
    assert ledger.call_stack_ids == []


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


def test_ambiguous_deferred_choices_return_live_wording_without_story_mutation(
    manager: ServiceManager, persistence, user: User,
) -> None:
    from tangl.prose.naming import NamedActor, NamingOperations, get_authorities
    from tangl.story import MenuBlock
    from tangl.vm import ResolutionPhase
    from tangl.vm.runtime.frame import PhaseCtx

    suggestion = "{{ reference(host) }} is performing"
    world = World.from_script_data(script_data={
        "label": "ambiguous_deferred_choices",
        "metadata": {"start_at": "s.hub"},
        "globals": {"text_template": "jinja", "naming_defaults": {"Actor": "concealed"}},
        "actors": {"rin": {"kind": NamedActor, "name": "Rin",
                           "anonymous_name": "the blonde girl"}},
        "scenes": {"s": {"blocks": {
            "hub": {"kind": MenuBlock, "menu_items": {"has_tags": ["activity"]}},
            "first": {"tags": ["activity"], "locals": {"action_text": suggestion},
                      "roles": {"host": {"actor_ref": "rin"}}},
            "second": {"tags": ["activity"], "locals": {"action_text": suggestion},
                       "roles": {"host": {"actor_ref": "rin"}}},
        }}},
    })
    world.extra_authorities.extend(get_authorities())
    created = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    edge_ids = {str(fragment.edge_id) for fragment in created.fragments
                if isinstance(fragment, ChoiceFragment)}
    assert len(edge_ids) == 2
    ledger = persistence[user.current_ledger_id]
    actor = ledger.graph.find_one(Selector(has_kind=NamedActor, label="rin"))
    assert actor.narrator_knowledge == {}

    for text in ["the blonde girl is performing", "Rin is performing"]:
        before = ledger.value_hash()
        result = manager.resolve_choice(user_id=user.uid, request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command=text),
        ))
        (event,) = result.ux_events
        assert event.event_type == "edge_ambiguous"
        assert result.fragments == [] and result.step == created.step
        assert {candidate["text"] for candidate in event.details["candidates"]} == {text}
        assert {candidate["edge_id"] for candidate in event.details["candidates"]} == edge_ids
        assert ledger.value_hash() == before
        if actor.peek_knowledge() is None:
            ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id,
                           current_phase=ResolutionPhase.JOURNAL)
            NamingOperations(ctx).introduce(actor)

    for edge_id in edge_ids:
        edge = ledger.graph.get(UUID(edge_id))
        assert edge.text == "" and edge.successor.locals["action_text"] == suggestion

    edge.successor.locals["action_text"] = "{{ introduce(host) }}"
    actor.narrator_knowledge.clear()
    before = ledger.value_hash()
    with pytest.raises(RuntimeError, match="Introductions require"):
        manager.resolve_choice(user_id=user.uid, request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command="Rin"),
        ))
    assert ledger.value_hash() == before
    assert actor.narrator_knowledge == {}


@pytest.mark.parametrize("ambiguous", [False, True])
def test_command_lookup_never_evaluates_or_exposes_hidden_unavailable_choices(
    manager: ServiceManager, persistence, user: User, ambiguous: bool,
) -> None:
    actions = [
        {"label": "go_alias", "text": "Go", "successor": "good"},
        {"conditions": ["False"], "successor": "bad"},
        {"label": "hidden_explicit", "text": "Go", "conditions": ["False"],
         "successor": "bad"},
    ]
    world = World.from_script_data(script_data={
        "label": "hidden_choice_command",
        "metadata": {"start_at": "s.hub"},
        "globals": {"text_template": "jinja", "unavailable_choice_disclosure": "hide"},
        "scenes": {"s": {"blocks": {
            "hub": {"kind": MenuBlock, "actions": actions,
                    "menu_items": {"has_tags": ["offered"]}},
            "good": {"content": "You went."},
            "other": {"locals": {"action_text": "Go"},
                      "tags": ["offered"] if ambiguous else []},
            "bad": {"locals": {"action_text": "{{ missing_host.name }}"}},
        }}},
    })
    created = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    visible_ids = {str(f.edge_id) for f in created.fragments if isinstance(f, ChoiceFragment)}
    assert len(visible_ids) == (2 if ambiguous else 1)
    ledger = persistence[user.current_ledger_id]
    all_ids = set(ledger.graph.members)
    before = ledger.value_hash()
    hidden = ledger.graph.find_one(Selector(has_kind=Action, text=""))
    assert hidden.successor.label == "bad"
    with pytest.raises(ValueError, match="Edge validation failed"):
        manager.resolve_choice(user_id=user.uid, request=DirectEdgeRequest(edge_id=hidden.uid))
    assert ledger.value_hash() == before
    for command in ["unknown", hidden.get_label(), "hidden_explicit"]:
        result = manager.resolve_choice(user_id=user.uid, request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command=command),
        ))
        assert result.ux_events[0].event_type == "edge_not_found"
        assert ledger.value_hash() == before and set(ledger.graph.members) == all_ids
    result = manager.resolve_choice(user_id=user.uid, request=FindEdgeRequest(
        find_edge=CommandEdgeQuery(command="Go"),
    ))
    if ambiguous:
        (event,) = result.ux_events
        assert event.event_type == "edge_ambiguous"
        assert {item["edge_id"] for item in event.details["candidates"]} == visible_ids
        assert {item["text"] for item in event.details["candidates"]} == {"Go"}
        assert ledger.value_hash() == before
    else:
        assert result.ux_events == []
        assert ledger.cursor.label == "good"
    assert set(ledger.graph.members) == all_ids


@pytest.mark.parametrize("available", [False, True])
def test_command_lookup_preserves_diagnostics_for_visible_broken_wording(
    manager: ServiceManager, persistence, user: User, available: bool,
) -> None:
    world = World.from_script_data(script_data={
        "label": "visible_choice_error",
        "metadata": {"start_at": "s.hub"},
        "globals": {"text_template": "jinja", "unavailable_choice_disclosure": "hide"},
        "scenes": {"s": {"blocks": {
            "hub": {"actions": [
                {"text": "Go", "successor": "good"},
                {"conditions": ["False"], "successor": "bad"},
            ]},
            "good": {},
            "bad": {"locals": {"action_text": "{{ missing_host.name }}"}},
        }}},
    })
    manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    ledger = persistence[user.current_ledger_id]
    if available:
        ledger.graph.find_one(Selector(has_kind=Action, text="")).availability = []
    else:
        ledger.graph.locals["unavailable_choice_disclosure"] = "disclose"
    before = ledger.value_hash()
    with pytest.raises(UndefinedError, match="missing_host"):
        manager.resolve_choice(user_id=user.uid, request=FindEdgeRequest(
            find_edge=CommandEdgeQuery(command="Go"),
        ))
    assert ledger.value_hash() == before


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
            "replaces_text": False,
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
    assert isinstance(world_info, ProjectedState)
    assert [channel.channel_id for channel in world_info.channels] == [
        "ui-style-hints-html",
        "ui-branding",
    ]
    selected = manager.get_world_info(
        world_id=loaded_world_label,
        channels=["ui-branding", "ui-style-hints-html", "ui-branding"],
    )
    assert [section.section_id for section in selected.sections] == [
        "ui-branding",
        "ui-style-hints-html",
    ]
    assert isinstance(selected.sections[0].value, BrandingValue)
    assert isinstance(selected.sections[1].value, TableValue)

    with pytest.raises(ValueError, match="Unknown info channel"):
        manager.get_world_info(world_id=loaded_world_label, channels=["ui-unknown"])

    system_info = manager.get_system_info()
    assert system_info.engine


def test_world_info_discloses_declared_stage_extent_only(manager: ServiceManager) -> None:
    manager.load_world(
        script_data=_story_script(stage_extent={"width": 640, "height": 400})
    )

    discovered = manager.get_world_info(world_id="service_manager_world")
    assert [channel.channel_id for channel in discovered.channels] == [
        "ui-style-hints-html",
        "ui-branding",
        "ui-stage",
    ]

    selected = manager.get_world_info(
        world_id="service_manager_world",
        channels=["ui-stage"],
    )
    assert len(selected.sections) == 1
    assert selected.sections[0].section_id == "ui-stage"
    assert selected.sections[0].value == StageExtentValue(width=640, height=400)


@pytest.mark.parametrize(
    "stage_extent",
    [
        {"width": 0, "height": 200},
        {"width": "320", "height": 200},
    ],
)
def test_world_info_refuses_to_advertise_malformed_stage_extent(
    manager: ServiceManager,
    stage_extent: dict[str, object],
) -> None:
    manager.load_world(script_data=_story_script(stage_extent=stage_extent))

    with pytest.raises(ValueError):
        manager.get_world_info(world_id="service_manager_world")


def test_create_user_restores_an_existing_recovery_secret(
    manager: ServiceManager,
    persistence,
) -> None:
    first = manager.create_user(secret="recovery-secret")
    second = manager.create_user(secret="recovery-secret")

    assert first.details["user_id"] == second.details["user_id"]
    assert len([item for item in persistence.values() if isinstance(item, User)]) == 1


def test_create_user_rerolls_a_generated_codename_collision(
    manager: ServiceManager,
    persistence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    occupied = manager.create_user(secret="occupied-codename")
    generated_names = iter(["occupied-codename", "free-codename"])
    monkeypatch.setattr(
        "tangl.service.service_manager.get_code_name",
        lambda: next(generated_names),
    )

    created = manager.create_user()

    assert created.details["user_secret"] == "free-codename"
    assert created.details["user_id"] != occupied.details["user_id"]
    assert len([item for item in persistence.values() if isinstance(item, User)]) == 2


def _run_persisted_user_process(*, storage_path: Path, secret: str) -> tuple[str, int]:
    source_path = Path(__file__).resolve().parents[2] / "src"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(source_path), environment.get("PYTHONPATH")) if part
    )
    program = "\n".join(
        [
            "from pathlib import Path",
            "import sys",
            "from tangl.persistence import PersistenceManagerFactory",
            "from tangl.service.service_manager import ServiceManager",
            "persistence = PersistenceManagerFactory.json_file(base_path=Path(sys.argv[1]))",
            "result = ServiceManager(persistence).create_user(secret=sys.argv[2])",
            "print(f\"{result.details['user_id']};{len(list(persistence.values()))}\")",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", program, str(storage_path), secret],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    user_id, user_count = completed.stdout.strip().split(";", maxsplit=1)
    return user_id, int(user_count)


def test_create_user_restores_persisted_recovery_codename_after_restart(
    tmp_path: Path,
) -> None:
    created_id, created_count = _run_persisted_user_process(
        storage_path=tmp_path,
        secret="persistent-codename",
    )
    restored_id, restored_count = _run_persisted_user_process(
        storage_path=tmp_path,
        secret="persistent-codename",
    )

    assert restored_id == created_id
    assert created_count == restored_count == 1
