"""Service38 REST dependencies (gateway + shared locks)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from tangl.rest.dependencies import get_orchestrator
from tangl.service38 import ServiceGateway38, build_service_gateway38

_gateway38: ServiceGateway38 | None = None
_user_locks38: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


def _build_service_gateway38() -> ServiceGateway38:
    base_orchestrator = get_orchestrator()
    return build_service_gateway38(base_orchestrator.persistence)


def get_service_gateway38() -> ServiceGateway38:
    """Return process-wide service38 gateway singleton."""

    global _gateway38
    if _gateway38 is None:
        _gateway38 = _build_service_gateway38()
    return _gateway38


def get_user_locks38() -> dict[UUID, asyncio.Lock]:
    """Provide per-user asyncio locks for service38 routes."""

    return _user_locks38


def reset_service_gateway38_for_testing() -> None:
    """Reset cached service38 gateway singleton (testing hook)."""

    global _gateway38
    _gateway38 = None
    _user_locks38.clear()
