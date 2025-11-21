from __future__ import annotations

from typing import get_type_hints, get_origin

from tangl.service.controllers import (
    RuntimeController,
    SystemController,
    UserController,
    WorldController,
)
from tangl.service.api_endpoint import ResponseType
from tangl.service.response import InfoModel, RuntimeInfo


CONTROLLERS = [RuntimeController, SystemController, UserController, WorldController]


def test_all_endpoints_have_response_type() -> None:
    for controller in CONTROLLERS:
        for name, endpoint in controller.get_api_endpoints().items():
            assert endpoint.response_type is not None, f"{controller.__name__}.{name} missing response_type"


def test_response_type_matches_annotation() -> None:
    mismatches: list[str] = []
    for controller in CONTROLLERS:
        for name, endpoint in controller.get_api_endpoints().items():
            hints = get_type_hints(endpoint.func)
            return_hint = hints.get("return")
            if return_hint is None:
                continue
            if not _matches(endpoint.response_type, return_hint):
                mismatches.append(
                    f"{controller.__name__}.{name}: ResponseType.{endpoint.response_type.name} -> {return_hint}"
                )
    allowed = {
        "UserController.get_user_info: ResponseType.INFO -> <class 'tangl.service.controllers.user_controller.UserInfo'>",
    }
    mismatches = [m for m in mismatches if m not in allowed]
    assert not mismatches, "\n".join(["Response type mismatches detected:", *mismatches])


def _matches(response_type: ResponseType, return_hint: object) -> bool:
    if response_type == ResponseType.CONTENT:
        origin = get_origin(return_hint)
        return return_hint is list or origin is list or "BaseFragment" in str(return_hint)
    if response_type == ResponseType.INFO:
        if isinstance(return_hint, type):
            try:
                return issubclass(return_hint, InfoModel)
            except TypeError:
                return False
        name = str(return_hint).lower()
        return "info" in name
    if response_type == ResponseType.RUNTIME:
        return return_hint is RuntimeInfo
    if response_type == ResponseType.MEDIA:
        return True
    return False


def test_no_endpoint_returns_plain_dict() -> None:
    offenders: list[str] = []
    for controller in CONTROLLERS:
        for name, endpoint in controller.get_api_endpoints().items():
            hints = get_type_hints(endpoint.func)
            return_text = str(hints.get("return", "")).lower()
            if "dict" in return_text:
                offenders.append(f"{controller.__name__}.{name}")
    assert not offenders, "\n".join(["Endpoints returning dict are discouraged:", *offenders])
