"""REST gateway dependencies (service adapter + shared locks)."""

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

_gateway: ServiceGateway | None = None
_adapter: GatewayRestAdapter | None = None
_user_locks: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_api_key_index: dict[str, UUID] = {}


def _build_service_gateway() -> ServiceGateway:
    base_orchestrator = get_orchestrator()
    return build_service_gateway(base_orchestrator.persistence)


def get_service_gateway() -> ServiceGateway:
    """Return process-wide service gateway singleton."""

    global _gateway
    if _gateway is None:
        _gateway = _build_service_gateway()
    return _gateway


def _resolve_user_auth_from_key(
    api_key: str,
    *,
    gateway: ServiceGateway | None = None,
) -> UserAuthInfo:
    service_gateway = gateway or get_service_gateway()
    auth = user_id_by_key(
        api_key,
        service_gateway.persistence,
        reverse_index=_api_key_index,
    )
    if auth is None:
        raise ValueError("Invalid API key")
    return auth


def _build_service_adapter() -> GatewayRestAdapter:
    gateway = get_service_gateway()
    resolver: Callable[[str], UserAuthInfo] = (
        lambda api_key: _resolve_user_auth_from_key(api_key, gateway=gateway)
    )
    return GatewayRestAdapter(gateway, auth_resolver=resolver)


def get_service_adapter() -> GatewayRestAdapter:
    """Return process-wide REST adapter singleton."""

    global _adapter
    if _adapter is None:
        _adapter = _build_service_adapter()
    return _adapter


def get_user_locks() -> dict[UUID, asyncio.Lock]:
    """Provide per-user asyncio locks for story routes."""

    return _user_locks


def resolve_user_auth(
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


def resolve_user_id(
    api_key: str,
    *,
    gateway: ServiceGateway | None = None,  # backward-compat call sites
    adapter: GatewayRestAdapter | None = None,
) -> UUID:
    """Resolve API key to user id for user-scoped operations."""

    return resolve_user_auth(api_key, gateway=gateway, adapter=adapter).user_id


def reset_service_gateway_for_testing() -> None:
    """Reset cached service gateway singleton (testing hook)."""

    global _gateway, _adapter
    _gateway = None
    _adapter = None
    _user_locks.clear()
    _api_key_index.clear()
