"""Transport-facing adapter helpers for service gateway execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from uuid import UUID

from .auth import UserAuthInfo
from .gateway import ServiceGateway
from .operations import ServiceOperation

AuthResolver = Callable[[str], UserAuthInfo]
# Backwards-compatible alias retained during naming cutover.
AuthResolver38 = AuthResolver


@dataclass(frozen=True)
class GatewayRequest:
    """Operation request envelope consumed by :class:`GatewayRestAdapter`."""

    operation: ServiceOperation
    params: Mapping[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    user_auth: UserAuthInfo | None = None
    render_profile: str | None = None


class GatewayRestAdapter:
    """Thin adapter that normalizes transport calls onto ``ServiceGateway``."""

    def __init__(
        self,
        gateway: ServiceGateway,
        *,
        auth_resolver: AuthResolver | None = None,
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

    def execute_request(self, request: GatewayRequest) -> Any:
        """Execute a prepared gateway request envelope."""

        return self.gateway.execute(
            request.operation,
            user_id=request.user_id,
            user_auth=request.user_auth,
            render_profile=request.render_profile or self.default_render_profile,
            **dict(request.params),
        )

    def execute_operation(
        self,
        operation: ServiceOperation,
        /,
        *,
        user_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
        render_profile: str | None = None,
        **params: Any,
    ) -> Any:
        """Execute an operation with explicit parameters."""

        return self.gateway.execute(
            operation,
            user_id=user_id,
            user_auth=user_auth,
            render_profile=render_profile or self.default_render_profile,
            **params,
        )

    def execute_authenticated(
        self,
        api_key: str,
        operation: ServiceOperation,
        /,
        *,
        render_profile: str | None = None,
        **params: Any,
    ) -> Any:
        """Resolve ``api_key`` then execute user-scoped operation."""

        user_auth = self.resolve_user_auth(api_key)
        return self.execute_operation(
            operation,
            user_id=user_auth.user_id,
            user_auth=user_auth,
            render_profile=render_profile,
            **params,
        )


# Backwards-compatible aliases retained during naming cutover.
GatewayRequest38 = GatewayRequest
GatewayRestAdapter38 = GatewayRestAdapter


__all__ = [
    "AuthResolver",
    "AuthResolver38",
    "GatewayRequest",
    "GatewayRequest38",
    "GatewayRestAdapter",
    "GatewayRestAdapter38",
]
