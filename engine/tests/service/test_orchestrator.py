from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from tangl.core import BaseFragment
from tangl.service import ApiEndpoint, HasApiEndpoints, MethodType, Orchestrator, ResponseType
from tangl.service.exceptions import InvalidOperationError
from tangl.service.response import InfoModel, RuntimeInfo


class _SampleInfo(InfoModel):
    value: str


class _GoodController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
    def info(self) -> _SampleInfo:
        return _SampleInfo(value="ok")


class _BadController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
    def broken(self) -> RuntimeInfo:
        return {"oops": True}  # type: ignore[return-value]


class _FailingController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
    def failing(self) -> RuntimeInfo:
        raise InvalidOperationError("nope")


@pytest.fixture
def orchestrator() -> Orchestrator:
    orch = Orchestrator(persistence_manager=None)
    return orch


def test_execute_returns_native_response(orchestrator: Orchestrator) -> None:
    orchestrator.register_controller(_GoodController)
    result = orchestrator.execute("_GoodController.info")
    assert isinstance(result, _SampleInfo)


def test_orchestrator_validates_response_type(orchestrator: Orchestrator) -> None:
    orchestrator.register_controller(_BadController)
    with pytest.raises(TypeError):
        orchestrator.execute("_BadController.broken")


def test_orchestrator_maps_service_errors(orchestrator: Orchestrator) -> None:
    orchestrator.register_controller(_FailingController)
    result = orchestrator.execute("_FailingController.failing")
    assert isinstance(result, RuntimeInfo)
    assert result.status == "error"
    assert result.code == InvalidOperationError.code


def test_orchestrator_bubbles_non_service_errors(orchestrator: Orchestrator) -> None:
    class _BuggyController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.UPDATE)
        def buggy(self) -> RuntimeInfo:
            raise ValueError("boom")

    orchestrator.register_controller(_BuggyController)
    with pytest.raises(ValueError):
        orchestrator.execute("_BuggyController.buggy")


def test_orchestrator_cleanup_invalid_delete_id_with_no_persistence() -> None:
    class _CleanupController(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.READ)
        def cleanup(self) -> RuntimeInfo:
            return RuntimeInfo.ok(_delete_ledger_id="not-a-uuid")

    orch = Orchestrator(persistence_manager=None)
    orch.register_controller(_CleanupController)

    result = orch.execute("_CleanupController.cleanup")
    assert isinstance(result, RuntimeInfo)
    assert result.details is not None
    assert "_delete_ledger_id" not in result.details
    assert result.details["persistence_deleted"] is False


def test_orchestrator_cleanup_mapping_result_deletes_from_persistence() -> None:
    ledger_id = uuid4()
    store: dict[Any, Any] = {ledger_id: {"ledger_uid": ledger_id}}

    class _DictCleanup(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.MEDIA, method_type=MethodType.READ)
        def cleanup(self) -> dict[str, Any]:
            return {"_delete_ledger_id": str(ledger_id)}

    orch = Orchestrator(store)
    orch.register_controller(_DictCleanup)

    result = orch.execute("_DictCleanup.cleanup")
    assert isinstance(result, dict)
    assert "_delete_ledger_id" not in result
    assert result["persistence_deleted"] is True
    assert ledger_id not in store


def test_orchestrator_cleanup_mapping_result_deletes_string_key() -> None:
    ledger_id = uuid4()
    store: dict[Any, Any] = {str(ledger_id): {"ledger_uid": ledger_id}}

    class _DictCleanupStrKey(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.MEDIA, method_type=MethodType.READ)
        def cleanup(self) -> dict[str, Any]:
            return {"_delete_ledger_id": str(ledger_id)}

    orch = Orchestrator(store)
    orch.register_controller(_DictCleanupStrKey)

    result = orch.execute("_DictCleanupStrKey.cleanup")
    assert result["persistence_deleted"] is True
    assert ledger_id not in store
    assert str(ledger_id) not in store


class _Frag(BaseFragment):
    text: str


class _ContentController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.CONTENT, method_type=MethodType.READ)
    def good_content(self) -> list[_Frag]:
        return [_Frag(text="hello")]

    @ApiEndpoint.annotate(response_type=ResponseType.CONTENT, method_type=MethodType.READ)
    def bad_content_type(self) -> list[int]:
        return [1, 2, 3]  # type: ignore[return-value]

    @ApiEndpoint.annotate(response_type=ResponseType.CONTENT, method_type=MethodType.READ)
    def not_a_list(self) -> _Frag:
        return _Frag(text="nope")  # type: ignore[return-value]


def test_orchestrator_validates_content_response_type() -> None:
    orch = Orchestrator(persistence_manager=None)
    orch.register_controller(_ContentController)

    result = orch.execute("_ContentController.good_content")
    assert isinstance(result, list)
    assert all(isinstance(item, _Frag) for item in result)

    with pytest.raises(TypeError, match="declared ResponseType.CONTENT .* non-BaseFragment"):
        orch.execute("_ContentController.bad_content_type")

    with pytest.raises(TypeError, match="declared ResponseType.CONTENT"):
        orch.execute("_ContentController.not_a_list")


class _MediaController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.MEDIA, method_type=MethodType.READ)
    def media(self) -> dict[str, Any]:
        return {"payload": "raw-bytes-or-whatever"}


def test_orchestrator_skips_media_validation() -> None:
    orch = Orchestrator(persistence_manager=None)
    orch.register_controller(_MediaController)

    result = orch.execute("_MediaController.media")
    assert isinstance(result, dict)
    assert result["payload"] == "raw-bytes-or-whatever"
