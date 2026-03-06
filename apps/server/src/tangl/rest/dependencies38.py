"""Service38 REST dependencies (gateway + shared locks)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Callable
from uuid import UUID

from fastapi import HTTPException

from tangl.rest.dependencies import get_orchestrator
from tangl.service import (
    GatewayRestAdapter,
    ServiceGateway,
    UserAuthInfo,
    build_service_gateway,
    user_id_by_key,
)

_gateway38: ServiceGateway | None = None
_adapter38: GatewayRestAdapter | None = None
_user_locks38: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_api_key_index38: dict[str, UUID] = {}


def _build_service_gateway38() -> ServiceGateway:
    base_orchestrator = get_orchestrator()
    return build_service_gateway(base_orchestrator.persistence)


def get_service_gateway38() -> ServiceGateway:
    """Return process-wide service38 gateway singleton."""

    global _gateway38
    if _gateway38 is None:
        _gateway38 = _build_service_gateway38()
    return _gateway38


def _resolve_user_auth_from_key(
    api_key: str,
    *,
    gateway: ServiceGateway | None = None,
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


def _build_service_adapter38() -> GatewayRestAdapter:
    gateway = get_service_gateway38()
    resolver: Callable[[str], UserAuthInfo] = (
        lambda api_key: _resolve_user_auth_from_key(api_key, gateway=gateway)
    )
    return GatewayRestAdapter(gateway, auth_resolver=resolver)


def get_service_adapter38() -> GatewayRestAdapter:
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
    gateway: ServiceGateway | None = None,  # backward-compat call sites
    adapter: GatewayRestAdapter | None = None,
) -> UserAuthInfo:
    """Resolve API key to user auth context for route handlers."""

    try:
        if adapter is not None:
            return adapter.resolve_user_auth(api_key)
        return _resolve_user_auth_from_key(api_key, gateway=gateway)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def resolve_user_id38(
    api_key: str,
    *,
    gateway: ServiceGateway | None = None,  # backward-compat call sites
    adapter: GatewayRestAdapter | None = None,
) -> UUID:
    """Resolve API key to user id for user-scoped operations."""

    return resolve_user_auth38(api_key, gateway=gateway, adapter=adapter).user_id


def reset_service_gateway38_for_testing() -> None:
    """Reset cached service38 gateway singleton (testing hook)."""

    global _gateway38, _adapter38
    _gateway38 = None
    _adapter38 = None
    _user_locks38.clear()
    _api_key_index38.clear()
