from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from tangl.core import Graph, StreamRegistry
from tangl.core import Graph as Graph38
from tangl.service import AccessLevel, ApiEndpoint, HasApiEndpoints, MethodType, ResponseType
from tangl.service.exceptions import AccessDeniedError
from tangl.service.response import RuntimeInfo as LegacyRuntimeInfo
from tangl.service.user.user import User
from tangl.service import (
    ApiEndpoint38,
    Orchestrator38,
    ServiceOperation38,
    UserAuthInfo,
    WritebackMode,
)
from tangl.service.gateway import ServiceGateway38
from tangl.service.hooks import GatewayHooks, HookPhase
from tangl.service.response import InfoModel, RuntimeInfo
from tangl.vm import Ledger
from tangl.vm.runtime.ledger import Ledger as Ledger38

SAVE_KEY_ERROR = "missing save key"


class FakePersistence(dict):
    def __init__(self) -> None:
        super().__init__()
        self.get_requests: list[UUID] = []
        self.saved: list[object] = []

    def get(self, key, default=None):
        self.get_requests.append(key)
        return super().get(key, default)

    def save(self, value) -> None:
        self.saved.append(value)
        key = getattr(value, "uid", None)
        if key is None and isinstance(value, dict):
            key = value.get("uid") or value.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to determine key for saved value")
        super().__setitem__(key, value)


class RoundTripPersistence(dict):
    """Persistence shim that stores ledgers as unstructured payloads."""

    def save(self, value) -> None:
        key = getattr(value, "uid", None)
        if key is None:
            raise ValueError(SAVE_KEY_ERROR)
        if hasattr(value, "unstructure"):
            super().__setitem__(key, value.unstructure())
        else:
            super().__setitem__(key, value)


class WorldInfo(InfoModel):
    world: str


class CursorInfo(InfoModel):
    cursor_id: UUID


@pytest.fixture
def fake_persistence() -> FakePersistence:
    return FakePersistence()


@pytest.fixture
def minimal_ledger() -> Ledger:
    graph = Graph()
    start = graph.add_node(label="start")
    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()
    return ledger


def test_orchestrator38_preprocessor_sees_non_signature_kwargs() -> None:
    seen_world_ids: list[str | None] = []

    def dereference_world(args, kwargs):
        seen_world_ids.append(kwargs.get("world_id"))
        world_id = kwargs.pop("world_id", None)
        if world_id is not None:
            kwargs["world"] = f"world:{world_id}"
        return args, kwargs

    class _WorldController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            preprocessors=[dereference_world],
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def get_world_info(self, world: str) -> WorldInfo:
            return WorldInfo(world=world)

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_WorldController)

    result = orchestrator.execute("_WorldController.get_world_info", world_id="demo")

    assert isinstance(result, WorldInfo)
    assert result.world == "world:demo"
    assert seen_world_ids == ["demo"]


def test_orchestrator38_rejects_leftover_kwargs_after_preprocessing() -> None:
    class _WorldController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def get_world_info(self, world: str) -> WorldInfo:
            return WorldInfo(world=world)

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_WorldController)

    with pytest.raises(TypeError, match="argument binding failed"):
        orchestrator.execute("_WorldController.get_world_info", world_id="demo")


def test_orchestrator38_writeback_modes(
    fake_persistence: FakePersistence,
    minimal_ledger: Ledger,
) -> None:
    class _ReadController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def get_cursor(self, ledger: Ledger) -> CursorInfo:
            return CursorInfo(cursor_id=ledger.cursor_id)

    class _UpdateController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
        def update_step(self, ledger: Ledger) -> RuntimeInfo:
            ledger.step += 1
            return RuntimeInfo.ok(step=ledger.step)

    fake_persistence[minimal_ledger.uid] = minimal_ledger.unstructure()

    orchestrator = Orchestrator38(fake_persistence)
    orchestrator.register_controller(_ReadController)
    orchestrator.register_controller(_UpdateController)

    fake_persistence.saved.clear()
    orchestrator.execute("_ReadController.get_cursor", ledger_id=minimal_ledger.uid)
    assert not fake_persistence.saved

    orchestrator.set_endpoint_policy(
        "_ReadController.get_cursor",
        writeback_mode=WritebackMode.ALWAYS,
    )
    fake_persistence.saved.clear()
    orchestrator.execute("_ReadController.get_cursor", ledger_id=minimal_ledger.uid)
    assert fake_persistence.saved

    orchestrator.set_endpoint_policy(
        "_UpdateController.update_step",
        writeback_mode=WritebackMode.NEVER,
    )
    fake_persistence.saved.clear()
    orchestrator.execute("_UpdateController.update_step", ledger_id=minimal_ledger.uid)
    assert not fake_persistence.saved


def test_orchestrator38_persist_paths_save_returned_payloads(fake_persistence: FakePersistence) -> None:
    class _CreateController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.CREATE)
        def create_story(self) -> RuntimeInfo:
            graph = Graph()
            start = graph.add_node(label="start")
            ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
            ledger.push_snapshot()
            return RuntimeInfo.ok(message="created", ledger=ledger)

        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.CREATE)
        def create_user(self) -> RuntimeInfo:
            user = User(label="player")
            return RuntimeInfo.ok(message="created", user=user, user_id=str(user.uid))

    orchestrator = Orchestrator38(fake_persistence)
    orchestrator.register_controller(_CreateController)

    orchestrator.set_endpoint_policy(
        "_CreateController.create_story",
        persist_paths=("details.ledger",),
    )
    orchestrator.set_endpoint_policy(
        "_CreateController.create_user",
        persist_paths=("details.user",),
    )

    fake_persistence.saved.clear()
    orchestrator.execute("_CreateController.create_story")
    assert any(hasattr(item, "cursor_id") for item in fake_persistence.saved)

    fake_persistence.saved.clear()
    orchestrator.execute("_CreateController.create_user")
    assert any(isinstance(item, User) for item in fake_persistence.saved)


def test_gateway_hooks_raw_and_html_profiles() -> None:
    hooks = GatewayHooks()
    hooks.install_default_hooks()

    raw_payload = RuntimeInfo.ok(content="**bold**")
    raw_result = hooks.run_outbound(
        raw_payload,
        operation=ServiceOperation38.SYSTEM_INFO,
        render_profile="raw",
        user_id=None,
    )
    assert isinstance(raw_result, RuntimeInfo)
    assert raw_result.details is not None
    assert raw_result.details.get("content") == "**bold**"

    html_payload = RuntimeInfo.ok(content="**bold**")
    html_result = hooks.run_outbound(
        html_payload,
        operation=ServiceOperation38.SYSTEM_INFO,
        render_profile="html",
        user_id=None,
    )
    assert isinstance(html_result, RuntimeInfo)
    assert html_result.details is not None
    assert "<strong>bold</strong>" in str(html_result.details.get("content"))


def test_orchestrator38_postprocessor_none_is_noop() -> None:
    def noop_postprocessor(_: Any) -> None:
        return None

    class _WorldController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            postprocessors=[noop_postprocessor],
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def get_world_info(self, world: str) -> WorldInfo:
            return WorldInfo(world=world)

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_WorldController)

    result = orchestrator.execute("_WorldController.get_world_info", world="demo")

    assert isinstance(result, WorldInfo)
    assert result.world == "demo"


def test_gateway_execute_endpoint_runs_inbound_hooks_for_unmapped_endpoint() -> None:
    hooks = GatewayHooks()
    hooks.install_default_hooks()

    @hooks.register_inbound(HookPhase.LATE)
    def _mark_unmapped_endpoint(
        params: dict[str, Any],
        *,
        operation: ServiceOperation38 | str,
        **_: Any,
    ):
        if isinstance(operation, str) and operation.startswith("endpoint:"):
            updated = dict(params)
            updated["world"] = f"hooked:{params.get('world')}"
            return updated
        return params

    class _WorldController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def get_world_info(self, world: str) -> WorldInfo:
            return WorldInfo(world=world)

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_WorldController)
    gateway = ServiceGateway38(orchestrator, hooks=hooks)

    result = gateway.execute_endpoint("_WorldController.get_world_info", world="demo")

    assert isinstance(result, WorldInfo)
    assert result.world == "hooked:demo"


def test_orchestrator38_runtime_response_coerces_legacy_runtimeinfo() -> None:
    class _LegacyController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
        def update_step(self) -> LegacyRuntimeInfo:
            return LegacyRuntimeInfo.ok(message="legacy", step=7)

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_LegacyController)

    result = orchestrator.execute("_LegacyController.update_step")

    assert isinstance(result, RuntimeInfo)
    assert result.message == "legacy"
    assert result.step == 7


def test_orchestrator38_round_trip_excluded_runtime_fields() -> None:
    class _LedgerController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.READ)
        def inspect_ledger(self, ledger: Ledger38) -> RuntimeInfo:
            return RuntimeInfo.ok(
                has_runtime_user=ledger.user is not None,
                user_id=str(ledger.user_id) if ledger.user_id else None,
            )

    graph = Graph38()
    start = graph.add_node(label="start")
    user = User(label="rt-player")
    ledger = Ledger38(graph=graph, cursor_id=start.uid)
    ledger.user = user
    ledger.user_id = user.uid

    persistence = RoundTripPersistence()
    persistence[ledger.uid] = ledger.unstructure()

    orchestrator = Orchestrator38(persistence)
    orchestrator.register_controller(_LedgerController)

    result = orchestrator.execute("_LedgerController.inspect_ledger", ledger_id=ledger.uid)

    assert isinstance(result, RuntimeInfo)
    assert result.details is not None
    assert result.details.get("has_runtime_user") is False
    assert result.details.get("user_id") == str(user.uid)


def test_orchestrator38_round_trip_ledger_writeback_remains_hydratable() -> None:
    class _LedgerController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
        def advance(self, ledger: Ledger38) -> RuntimeInfo:
            had_runtime_user = ledger.user is not None
            ledger.step += 1
            return RuntimeInfo.ok(
                step=ledger.step,
                had_runtime_user=had_runtime_user,
                user_id=str(ledger.user_id) if ledger.user_id else None,
            )

    graph = Graph38()
    start = graph.add_node(label="start")
    user = User(label="rt-player")
    ledger = Ledger38(graph=graph, cursor_id=start.uid)
    ledger.user = user
    ledger.user_id = user.uid

    persistence = RoundTripPersistence()
    persistence[ledger.uid] = ledger.unstructure()

    orchestrator = Orchestrator38(persistence)
    orchestrator.register_controller(_LedgerController)

    first = orchestrator.execute("_LedgerController.advance", ledger_id=ledger.uid)
    assert isinstance(first, RuntimeInfo)
    assert first.step == 1
    assert first.details is not None
    assert first.details.get("had_runtime_user") is False
    assert first.details.get("user_id") == str(user.uid)

    stored_after_first = persistence[ledger.uid]
    assert isinstance(stored_after_first, dict)
    assert stored_after_first.get("user_id") == str(user.uid)
    assert "user" not in stored_after_first

    second = orchestrator.execute("_LedgerController.advance", ledger_id=ledger.uid)
    assert isinstance(second, RuntimeInfo)
    assert second.step == 2
    assert second.details is not None
    assert second.details.get("had_runtime_user") is False


def test_orchestrator38_reattaches_runtime_user_when_user_is_hydrated() -> None:
    class _LedgerController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.READ)
        def inspect(self, ledger: Ledger38) -> RuntimeInfo:
            return RuntimeInfo.ok(
                has_runtime_user=ledger.user is not None,
                user_id=str(ledger.user_id) if ledger.user_id else None,
            )

    graph = Graph38()
    start = graph.add_node(label="start")
    user = User(label="rt-player")
    ledger = Ledger38(graph=graph, cursor_id=start.uid)
    ledger.user_id = user.uid

    persistence = RoundTripPersistence()
    persistence[user.uid] = user
    persistence[ledger.uid] = ledger.unstructure()

    orchestrator = Orchestrator38(persistence)
    orchestrator.register_controller(_LedgerController)

    result = orchestrator.execute(
        "_LedgerController.inspect",
        user_id=user.uid,
        ledger_id=ledger.uid,
    )

    assert isinstance(result, RuntimeInfo)
    assert result.details is not None
    assert result.details.get("has_runtime_user") is True
    assert result.details.get("user_id") == str(user.uid)


def test_orchestrator38_hydrates_user_by_param_name_not_type_suffix(
    fake_persistence: FakePersistence,
) -> None:
    class AccountState:
        def __init__(self, uid: UUID) -> None:
            self.uid = uid
            self.current_ledger_id = None

    class UserEcho(InfoModel):
        user_id: UUID

    class _AccountController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def who(self, user: AccountState) -> UserEcho:
            return UserEcho(user_id=user.uid)

    user_id = uuid4()
    fake_persistence[user_id] = AccountState(user_id)

    orchestrator = Orchestrator38(fake_persistence)
    orchestrator.register_controller(_AccountController)

    result = orchestrator.execute("_AccountController.who", user_id=user_id)
    assert isinstance(result, UserEcho)
    assert result.user_id == user_id


def test_orchestrator38_explicit_binds_override_signature_inference(
    fake_persistence: FakePersistence,
) -> None:
    class UserEcho(InfoModel):
        user_id: UUID

    class _AccountController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.USER,
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
            binds=(),
        )
        def who(self, user: User) -> UserEcho:
            return UserEcho(user_id=user.uid)

    user_id = uuid4()
    fake_persistence[user_id] = User(uid=user_id)

    orchestrator = Orchestrator38(fake_persistence)
    orchestrator.register_controller(_AccountController)

    with pytest.raises(TypeError, match="argument binding failed"):
        orchestrator.execute("_AccountController.who", user_id=user_id)


def test_orchestrator38_public_endpoint_allows_anonymous_calls() -> None:
    class _AccessController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.PUBLIC,
            method_type=MethodType.READ,
            response_type=ResponseType.RUNTIME,
            binds=(),
        )
        def public_status(self) -> RuntimeInfo:
            return RuntimeInfo.ok(message="public")

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_AccessController)

    result = orchestrator.execute("_AccessController.public_status")

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert result.message == "public"


def test_orchestrator38_user_endpoint_denies_when_no_user_context() -> None:
    class _AccessController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.USER,
            method_type=MethodType.READ,
            response_type=ResponseType.RUNTIME,
            binds=(),
        )
        def user_status(self) -> RuntimeInfo:
            return RuntimeInfo.ok(message="user")

    orchestrator = Orchestrator38(persistence_manager={})
    orchestrator.register_controller(_AccessController)

    with pytest.raises(AccessDeniedError, match="Access denied"):
        orchestrator.execute("_AccessController.user_status")


def test_orchestrator38_restricted_endpoint_denies_non_privileged_user() -> None:
    class _AccessController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.RESTRICTED,
            method_type=MethodType.READ,
            response_type=ResponseType.RUNTIME,
            binds=(),
        )
        def restricted_status(self) -> RuntimeInfo:
            return RuntimeInfo.ok(message="restricted")

    user = User(label="normal-user", privileged=False)
    persistence = {user.uid: user}

    orchestrator = Orchestrator38(persistence_manager=persistence)
    orchestrator.register_controller(_AccessController)

    with pytest.raises(AccessDeniedError, match="Access denied"):
        orchestrator.execute("_AccessController.restricted_status", user_id=user.uid)


def test_orchestrator38_restricted_endpoint_allows_privileged_user() -> None:
    class _AccessController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.RESTRICTED,
            method_type=MethodType.READ,
            response_type=ResponseType.RUNTIME,
            binds=(),
        )
        def restricted_status(self) -> RuntimeInfo:
            return RuntimeInfo.ok(message="restricted")

    user = User(label="admin-user", privileged=True)
    persistence = {user.uid: user}

    orchestrator = Orchestrator38(persistence_manager=persistence)
    orchestrator.register_controller(_AccessController)

    result = orchestrator.execute("_AccessController.restricted_status", user_id=user.uid)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert result.message == "restricted"


def test_orchestrator38_user_auth_context_is_authoritative() -> None:
    class _AccessController(HasApiEndpoints):
        @ApiEndpoint38.annotate(
            access_level=AccessLevel.RESTRICTED,
            method_type=MethodType.READ,
            response_type=ResponseType.RUNTIME,
            binds=(),
        )
        def restricted_status(self) -> RuntimeInfo:
            return RuntimeInfo.ok(message="restricted")

    user = User(label="normal-user", privileged=False)
    persistence = {user.uid: user}

    orchestrator = Orchestrator38(persistence_manager=persistence)
    orchestrator.register_controller(_AccessController)

    auth = UserAuthInfo(user_id=user.uid, access_level=AccessLevel.RESTRICTED)
    result = orchestrator.execute(
        "_AccessController.restricted_status",
        user_id=user.uid,
        user_auth=auth,
    )

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
