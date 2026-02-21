"""Transport-facing adapter helpers for service38 gateway execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from uuid import UUID

from .auth import UserAuthInfo
from .gateway import ServiceGateway38
from .operations import ServiceOperation38

AuthResolver38 = Callable[[str], UserAuthInfo]


@dataclass(frozen=True)
class GatewayRequest38:
    """Operation request envelope consumed by :class:`GatewayRestAdapter38`."""

    operation: ServiceOperation38
    params: Mapping[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    render_profile: str | None = None


class GatewayRestAdapter38:
    """Thin adapter that normalizes transport calls onto ``ServiceGateway38``."""

    def __init__(
        self,
        gateway: ServiceGateway38,
        *,
        auth_resolver: AuthResolver38 | None = None,
        default_render_profile: str = "raw",
    ) -> None:
        self.gateway = gateway
        self._auth_resolver = auth_resolver
        self.default_render_profile = default_render_profile

    @property
    def persistence(self) -> Any:
        """Expose persistence for transport-layer helpers."""

        return self.gateway.persistence

    def resolve_user_auth(self, api_key: str) -> UserAuthInfo:
        """Resolve API key into user auth context."""

        if self._auth_resolver is None:
            raise ValueError("API key authentication is not configured for this adapter")
        return self._auth_resolver(api_key)

    def resolve_user_id(self, api_key: str) -> UUID:
        """Resolve API key into user id."""

        return self.resolve_user_auth(api_key).user_id

    def execute_request(self, request: GatewayRequest38) -> Any:
        """Execute a prepared gateway request envelope."""

        return self.gateway.execute(
            request.operation,
            user_id=request.user_id,
            render_profile=request.render_profile or self.default_render_profile,
            **dict(request.params),
        )

    def execute_operation(
        self,
        operation: ServiceOperation38,
        /,
        *,
        user_id: UUID | None = None,
        render_profile: str | None = None,
        **params: Any,
    ) -> Any:
        """Execute an operation with explicit parameters."""

        return self.gateway.execute(
            operation,
            user_id=user_id,
            render_profile=render_profile or self.default_render_profile,
            **params,
        )

    def execute_authenticated(
        self,
        api_key: str,
        operation: ServiceOperation38,
        /,
        *,
        render_profile: str | None = None,
        **params: Any,
    ) -> Any:
        """Resolve ``api_key`` then execute user-scoped operation."""

        user_id = self.resolve_user_id(api_key)
        return self.execute_operation(
            operation,
            user_id=user_id,
            render_profile=render_profile,
            **params,
        )


__all__ = [
    "AuthResolver38",
    "GatewayRequest38",
    "GatewayRestAdapter38",
]
