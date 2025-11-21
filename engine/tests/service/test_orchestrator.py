from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.service import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    Orchestrator,
    ResponseType,
)
from tangl.service.exceptions import InvalidOperationError
from tangl.service.response import InfoModel, RuntimeInfo


class _SampleInfo(InfoModel):
    value: str


class _GoodController(HasApiEndpoints):
    @ApiEndpoint.annotate(
        response_type=ResponseType.INFO,
        method_type=MethodType.READ,
        access_level=AccessLevel.PUBLIC,
    )
    def info(self) -> _SampleInfo:
        return _SampleInfo(value="ok")


class _BadController(HasApiEndpoints):
    @ApiEndpoint.annotate(
        response_type=ResponseType.RUNTIME,
        method_type=MethodType.UPDATE,
        access_level=AccessLevel.PUBLIC,
    )
    def broken(self) -> RuntimeInfo:
        return {"oops": True}  # type: ignore[return-value]


class _FailingController(HasApiEndpoints):
    @ApiEndpoint.annotate(
        response_type=ResponseType.RUNTIME,
        method_type=MethodType.UPDATE,
        access_level=AccessLevel.PUBLIC,
    )
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
        @ApiEndpoint.annotate(
            response_type=ResponseType.RUNTIME,
            method_type=MethodType.UPDATE,
            access_level=AccessLevel.PUBLIC,
        )
        def buggy(self) -> RuntimeInfo:
            raise ValueError("boom")

    orchestrator.register_controller(_BuggyController)
    with pytest.raises(ValueError):
        orchestrator.execute("_BuggyController.buggy")
