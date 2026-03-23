"""REST service-manager dependencies and auth helpers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException

from tangl.rest.dependencies import get_persistence
from tangl.service import ServiceAccess, ServiceManager, UserAuthInfo, build_service_manager, user_id_by_key

_service_manager: ServiceManager | None = None
_user_locks: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_api_key_index: dict[str, UUID] = {}


def _build_service_manager() -> ServiceManager:
    return build_service_manager(get_persistence())


def get_service_manager() -> ServiceManager:
    """Return the process-wide service-manager singleton."""

    global _service_manager
    if _service_manager is None:
        _service_manager = _build_service_manager()
    return _service_manager


def _resolve_user_auth_from_key(
    api_key: str,
    *,
    service_manager: ServiceManager | None = None,
) -> UserAuthInfo:
    manager = service_manager or get_service_manager()
    auth = user_id_by_key(
        api_key,
        manager.persistence,
        reverse_index=_api_key_index,
    )
    if auth is None:
        raise ValueError("Invalid API key")
    return auth


def get_user_locks() -> dict[UUID, asyncio.Lock]:
    """Provide per-user asyncio locks for story routes."""

    return _user_locks


def resolve_user_auth(
    api_key: str,
    *,
    service_manager: ServiceManager | None = None,
) -> UserAuthInfo:
    """Resolve API key to user auth context for route handlers."""

    try:
        return _resolve_user_auth_from_key(api_key, service_manager=service_manager)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_service_access(
    method_name: str,
    *,
    user_auth: UserAuthInfo | None = None,
) -> None:
    """Enforce service-method access metadata for transport calls."""

    try:
        spec = ServiceManager.get_service_methods()[method_name]
    except KeyError as exc:  # pragma: no cover - programmer error
        raise RuntimeError(f"Unknown service method: {method_name}") from exc

    if spec.access == ServiceAccess.PUBLIC:
        return
    if user_auth is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if spec.access == ServiceAccess.DEV and not user_auth.is_privileged:
        raise HTTPException(status_code=403, detail="Access denied")


def reset_service_manager_for_testing() -> None:
    """Reset cached service-manager singleton (testing hook)."""

    global _service_manager
    _service_manager = None
    _user_locks.clear()
    _api_key_index.clear()

