"""Service38 Orchestrator contract and hydration tests.

This suite is the service38 replacement for:
  - ``engine/tests/service/test_orchestrator.py``
  - ``engine/tests/service/test_orchestrator_basic.py``

It focuses on response validation, error mapping, resource hydration, frame
reuse, writeback behavior, and cleanup semantics in ``Orchestrator``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from tangl.core import BaseFragment, Graph
from tangl.service.exceptions import InvalidOperationError
from tangl.service.user.user import User
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResourceBinding,
    ResponseType,
)
from tangl.service.orchestrator import Orchestrator
from tangl.service.response import InfoModel, RuntimeInfo
from tangl.vm.runtime.ledger import Ledger


class _FakePersistence(dict):
    """Minimal persistence shim for hydration/writeback checks."""

    def __init__(self) -> None:
        super().__init__()
        self.get_requests: list[Any] = []
        self.saved: list[Any] = []
        self.deleted: list[Any] = []

    def get(self, key: Any, default: Any = None) -> Any:
        self.get_requests.append(key)
        return super().get(key, default)

    def save(self, value: Any) -> None:
        self.saved.append(value)
        key = getattr(value, "uid", None)
        if key is None and isinstance(value, dict):
            key = value.get("uid") or value.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to determine key for saved value")
        super().__setitem__(key, value)

    def remove(self, key: Any) -> None:
        self.deleted.append(key)
        super().__delitem__(key)


class _SampleInfo(InfoModel):
    value: str


class _CursorInfo(InfoModel):
    cursor_id: UUID


class _Frag(BaseFragment):
    fragment_type: str = "test"
    text: str


def _make_ledger() -> Ledger:
    graph = Graph()
    start = graph.add_node(label="start")
    return Ledger.from_graph(graph=graph, entry_id=start.uid)


@pytest.fixture
def fake_persistence() -> _FakePersistence:
    return _FakePersistence()


@pytest.fixture
def orchestrator(fake_persistence: _FakePersistence) -> Orchestrator:
    return Orchestrator(fake_persistence)


def test_execute_returns_info_model(orchestrator: Orchestrator) -> None:
    class _GoodController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def info(self) -> _SampleInfo:
            return _SampleInfo(value="ok")

    orchestrator.register_controller(_GoodController)
    result = orchestrator.execute("_GoodController.info")
    assert isinstance(result, _SampleInfo)
    assert result.value == "ok"


def test_orchestrator_validates_runtime_response_type(orchestrator: Orchestrator) -> None:
    class _BadController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.UPDATE,
        )
        def broken(self) -> RuntimeInfo:
            return {"oops": True}  # type: ignore[return-value]

    orchestrator.register_controller(_BadController)
    with pytest.raises(TypeError):
        orchestrator.execute("_BadController.broken")


def test_orchestrator_maps_service_errors(orchestrator: Orchestrator) -> None:
    class _FailingController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.UPDATE,
        )
        def failing(self) -> RuntimeInfo:
            raise InvalidOperationError("nope")

    orchestrator.register_controller(_FailingController)
    result = orchestrator.execute("_FailingController.failing")
    assert isinstance(result, RuntimeInfo)
    assert result.status == "error"
    assert result.code == InvalidOperationError.code


def test_orchestrator_bubbles_non_service_errors(orchestrator: Orchestrator) -> None:
    class _BuggyController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.UPDATE,
        )
        def buggy(self) -> RuntimeInfo:
            raise ValueError("boom")

    orchestrator.register_controller(_BuggyController)
    with pytest.raises(ValueError):
        orchestrator.execute("_BuggyController.buggy")


def test_orchestrator_validates_content_response_type(orchestrator: Orchestrator) -> None:
    class _ContentController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.CONTENT,
            method_type=MethodType.READ,
        )
        def good_content(self) -> list[_Frag]:
            return [_Frag(text="hello")]

        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.CONTENT,
            method_type=MethodType.READ,
        )
        def bad_content_type(self) -> list[int]:
            return [1, 2, 3]  # type: ignore[return-value]

        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.CONTENT,
            method_type=MethodType.READ,
        )
        def not_a_list(self) -> _Frag:
            return _Frag(text="nope")  # type: ignore[return-value]

    orchestrator.register_controller(_ContentController)

    result = orchestrator.execute("_ContentController.good_content")
    assert isinstance(result, list)
    assert all(isinstance(item, _Frag) for item in result)

    with pytest.raises(TypeError, match="declared ResponseType.CONTENT"):
        orchestrator.execute("_ContentController.bad_content_type")

    with pytest.raises(TypeError, match="declared ResponseType.CONTENT"):
        orchestrator.execute("_ContentController.not_a_list")


def test_orchestrator_skips_media_validation(orchestrator: Orchestrator) -> None:
    class _MediaController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.MEDIA,
            method_type=MethodType.READ,
        )
        def media(self) -> dict[str, Any]:
            return {"payload": "raw-bytes-or-whatever"}

    orchestrator.register_controller(_MediaController)
    result = orchestrator.execute("_MediaController.media")
    assert isinstance(result, dict)
    assert result["payload"] == "raw-bytes-or-whatever"


def test_orchestrator_hydrates_user_and_ledger(
    orchestrator: Orchestrator,
    fake_persistence: _FakePersistence,
) -> None:
    class _LedgerController(HasApiEndpoints):
        def __init__(self) -> None:
            self.last_call: tuple[User, Ledger] | None = None

        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def get_cursor(self, user: User, ledger: Ledger) -> _CursorInfo:
            self.last_call = (user, ledger)
            return _CursorInfo(cursor_id=ledger.cursor_id)

    ledger = _make_ledger()
    user = User(label="player")
    user.current_ledger_id = ledger.uid
    fake_persistence[user.uid] = user
    fake_persistence[ledger.uid] = ledger.unstructure()

    orchestrator.register_controller(_LedgerController)
    result = orchestrator.execute("_LedgerController.get_cursor", user_id=user.uid)
    assert isinstance(result, _CursorInfo)
    assert result.cursor_id == ledger.cursor_id

    controller_instance = orchestrator._endpoints["_LedgerController.get_cursor"].controller
    assert controller_instance.last_call is not None
    hydrated_user, hydrated_ledger = controller_instance.last_call
    assert hydrated_user is user
    assert hydrated_ledger.uid == ledger.uid
    assert [k for k in fake_persistence.get_requests if k == ledger.uid] == [ledger.uid]


def test_orchestrator_requires_user_id_for_user_hydration(
    orchestrator: Orchestrator,
) -> None:
    class _NeedsUserController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.USER,),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def who(self, user: User) -> _SampleInfo:
            return _SampleInfo(value=user.label or "")

    orchestrator.register_controller(_NeedsUserController)
    with pytest.raises(ValueError, match="user_id is required"):
        orchestrator.execute("_NeedsUserController.who")


def test_orchestrator_reuses_cached_ledger_for_frame(
    orchestrator: Orchestrator,
    fake_persistence: _FakePersistence,
) -> None:
    class _FrameController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.LEDGER, ResourceBinding.FRAME),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def get_frame_data(self, ledger: Ledger, frame: Any) -> _CursorInfo:
            assert frame is not None
            return _CursorInfo(cursor_id=ledger.cursor_id)

    ledger = _make_ledger()
    fake_persistence[ledger.uid] = ledger.unstructure()

    orchestrator.register_controller(_FrameController)
    fake_persistence.get_requests.clear()
    orchestrator.execute("_FrameController.get_frame_data", ledger_id=ledger.uid)

    ledger_gets = [key for key in fake_persistence.get_requests if key == ledger.uid]
    assert len(ledger_gets) == 1


def test_orchestrator_persists_mutations_and_skips_read_writeback(
    fake_persistence: _FakePersistence,
) -> None:
    class _UpdateController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.LEDGER,),
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.UPDATE,
        )
        def update_step(self, ledger: Ledger) -> RuntimeInfo:
            ledger.step += 1
            return RuntimeInfo.ok(step=ledger.step)

    class _ReadController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.LEDGER,),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def get_cursor(self, ledger: Ledger) -> _CursorInfo:
            return _CursorInfo(cursor_id=ledger.cursor_id)

    ledger = _make_ledger()
    fake_persistence[ledger.uid] = ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(_UpdateController)
    orchestrator.register_controller(_ReadController)

    fake_persistence.saved.clear()
    orchestrator.execute("_UpdateController.update_step", ledger_id=ledger.uid)
    assert fake_persistence.saved

    fake_persistence.saved.clear()
    orchestrator.execute("_ReadController.get_cursor", ledger_id=ledger.uid)
    assert not fake_persistence.saved


def test_orchestrator_cleanup_invalid_delete_id_with_no_persistence() -> None:
    class _CleanupController(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.READ,
        )
        def cleanup(self) -> RuntimeInfo:
            return RuntimeInfo.ok(_delete_ledger_id="not-a-uuid")

    orchestrator = Orchestrator(persistence_manager=None)
    orchestrator.register_controller(_CleanupController)

    result = orchestrator.execute("_CleanupController.cleanup")
    assert isinstance(result, RuntimeInfo)
    details = dict(result.details or {})
    assert "_delete_ledger_id" not in details
    assert details.get("persistence_deleted") is False


def test_orchestrator_cleanup_mapping_result_deletes_from_persistence() -> None:
    ledger_id = uuid4()
    persistence: dict[Any, Any] = {ledger_id: {"ledger_uid": ledger_id}}

    class _DictCleanup(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(),
            response_type=ResponseType.MEDIA,
            method_type=MethodType.READ,
        )
        def cleanup(self) -> dict[str, Any]:
            return {"_delete_ledger_id": str(ledger_id)}

    orchestrator = Orchestrator(persistence)
    orchestrator.register_controller(_DictCleanup)

    result = orchestrator.execute("_DictCleanup.cleanup")
    assert isinstance(result, dict)
    assert "_delete_ledger_id" not in result
    assert result["persistence_deleted"] is True
    assert ledger_id not in persistence


def test_orchestrator_build_ledger_rejects_unsupported_payload(
    fake_persistence: _FakePersistence,
) -> None:
    bogus_id = uuid4()
    fake_persistence[bogus_id] = object()

    class _NeedsLedger(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.LEDGER,),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def needs_ledger(self, ledger: Ledger) -> _CursorInfo:
            return _CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(_NeedsLedger)

    with pytest.raises(TypeError, match="Unsupported ledger payload"):
        orchestrator.execute("_NeedsLedger.needs_ledger", ledger_id=bogus_id)


def test_orchestrator_requires_persistence_for_ledger_hydration() -> None:
    class _NeedsLedger(HasApiEndpoints):
        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            binds=(ResourceBinding.LEDGER,),
            response_type=ResponseType.INFO,
            method_type=MethodType.READ,
        )
        def needs_ledger(self, ledger: Ledger) -> _CursorInfo:
            return _CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator = Orchestrator(persistence_manager=None)
    orchestrator.register_controller(_NeedsLedger)

    with pytest.raises(RuntimeError, match="Persistence manager required for resource hydration"):
        orchestrator.execute("_NeedsLedger.needs_ledger", ledger_id=uuid4())
