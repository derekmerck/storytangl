from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from tangl.service38 import (
    GatewayRequest38,
    GatewayRestAdapter38,
    ServiceOperation38,
    UserAuthInfo,
)
from tangl.service38.api_endpoint import AccessLevel


@dataclass
class _StubGateway:
    persistence: dict[str, Any]

    def __post_init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def execute(
        self,
        operation: ServiceOperation38,
        *,
        user_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
        render_profile: str = "raw",
        **params: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "operation": operation,
                "user_id": user_id,
                "user_auth": user_auth,
                "render_profile": render_profile,
                "params": dict(params),
            }
        )
        return {"status": "ok"}


def test_gateway_rest_adapter38_execute_operation_uses_default_render_profile() -> None:
    gateway = _StubGateway(persistence={})
    adapter = GatewayRestAdapter38(gateway, default_render_profile="cli_ascii")
    user_id = uuid4()

    adapter.execute_operation(
        ServiceOperation38.STORY38_STATUS,
        user_id=user_id,
        include_debug=True,
    )

    call = gateway.calls[-1]
    assert call["operation"] == ServiceOperation38.STORY38_STATUS
    assert call["user_id"] == user_id
    assert call["render_profile"] == "cli_ascii"
    assert call["params"] == {"include_debug": True}


def test_gateway_rest_adapter38_execute_request_overrides_profile() -> None:
    gateway = _StubGateway(persistence={})
    adapter = GatewayRestAdapter38(gateway, default_render_profile="raw")
    user_id = uuid4()

    adapter.execute_request(
        GatewayRequest38(
            operation=ServiceOperation38.STORY38_UPDATE,
            user_id=user_id,
            render_profile="html",
            params={"limit": 5},
        )
    )

    call = gateway.calls[-1]
    assert call["operation"] == ServiceOperation38.STORY38_UPDATE
    assert call["user_id"] == user_id
    assert call["render_profile"] == "html"
    assert call["params"] == {"limit": 5}


def test_gateway_rest_adapter38_execute_authenticated_uses_auth_resolver() -> None:
    gateway = _StubGateway(persistence={})
    expected_user_id = uuid4()
    resolved_keys: list[str] = []

    def _resolver(api_key: str) -> UserAuthInfo:
        resolved_keys.append(api_key)
        return UserAuthInfo(user_id=expected_user_id, access_level=AccessLevel.RESTRICTED)

    adapter = GatewayRestAdapter38(gateway, auth_resolver=_resolver)
    adapter.execute_authenticated(
        "demo-key",
        ServiceOperation38.USER_INFO,
        render_profile="raw",
    )

    call = gateway.calls[-1]
    assert resolved_keys == ["demo-key"]
    assert call["operation"] == ServiceOperation38.USER_INFO
    assert call["user_id"] == expected_user_id
    assert call["user_auth"] is not None
    assert call["user_auth"].user_id == expected_user_id
