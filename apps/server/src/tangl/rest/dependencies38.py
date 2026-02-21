"""Service38 REST dependencies (gateway + shared locks)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Callable
from uuid import UUID

from tangl.rest.dependencies import get_orchestrator
from tangl.service38 import (
    GatewayRestAdapter38,
    ServiceGateway38,
    UserAuthInfo,
    build_service_gateway38,
    user_id_by_key,
)

_gateway38: ServiceGateway38 | None = None
_adapter38: GatewayRestAdapter38 | None = None
_user_locks38: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_api_key_index38: dict[str, UUID] = {}


def _build_service_gateway38() -> ServiceGateway38:
    base_orchestrator = get_orchestrator()
    return build_service_gateway38(base_orchestrator.persistence)


def get_service_gateway38() -> ServiceGateway38:
    """Return process-wide service38 gateway singleton."""

    global _gateway38
    if _gateway38 is None:
        _gateway38 = _build_service_gateway38()
    return _gateway38


def _resolve_user_auth_from_key(
    api_key: str,
    *,
    gateway: ServiceGateway38 | None = None,
) -> UserAuthInfo:
    service_gateway = gateway or get_service_gateway38()
    auth = user_id_by_key(
        api_key,
        service_gateway.persistence,
        reverse_index=_api_key_index38,
    )
    if auth is None:
        raise ValueError("Invalid API key")
    return auth


def _build_service_adapter38() -> GatewayRestAdapter38:
    gateway = get_service_gateway38()
    resolver: Callable[[str], UserAuthInfo] = (
        lambda api_key: _resolve_user_auth_from_key(api_key, gateway=gateway)
    )
    return GatewayRestAdapter38(gateway, auth_resolver=resolver)


def get_service_adapter38() -> GatewayRestAdapter38:
    """Return process-wide service38 REST adapter singleton."""

    global _adapter38
    if _adapter38 is None:
        _adapter38 = _build_service_adapter38()
    return _adapter38


def get_user_locks38() -> dict[UUID, asyncio.Lock]:
    """Provide per-user asyncio locks for service38 routes."""

    return _user_locks38


def resolve_user_auth38(
    api_key: str,
    *,
    gateway: ServiceGateway38 | None = None,  # backward-compat call sites
) -> UserAuthInfo:
    """Resolve API key to user auth context for route handlers."""

    return _resolve_user_auth_from_key(api_key, gateway=gateway)


def resolve_user_id38(
    api_key: str,
    *,
    gateway: ServiceGateway38 | None = None,  # backward-compat call sites
) -> UUID:
    """Resolve API key to user id for user-scoped operations."""

    return resolve_user_auth38(api_key, gateway=gateway).user_id


def reset_service_gateway38_for_testing() -> None:
    """Reset cached service38 gateway singleton (testing hook)."""

    global _gateway38, _adapter38
    _gateway38 = None
    _adapter38 = None
    _user_locks38.clear()
    _api_key_index38.clear()
