"""Shared FastAPI dependencies for the StoryTangl REST app."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from tangl.persistence import PersistenceManagerFactory
from tangl.service import Orchestrator
from tangl.service.controllers import (
    RuntimeController,
    SystemController,
    UserController,
    WorldController,
)

_orchestrator: Orchestrator | None = None
_user_locks: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


def _build_orchestrator() -> Orchestrator:
    persistence = PersistenceManagerFactory.create_persistence_manager()
    orchestrator = Orchestrator(persistence)
    for controller in (
        RuntimeController,
        UserController,
        SystemController,
        WorldController,
    ):
        orchestrator.register_controller(controller)
    return orchestrator


def get_orchestrator() -> Orchestrator:
    """Return a process-wide orchestrator singleton."""

    global _orchestrator
    if _orchestrator is None:
        _orchestrator = _build_orchestrator()
    return _orchestrator


def get_user_locks() -> dict[UUID, asyncio.Lock]:
    """Provide a mapping of per-user asyncio locks."""

    return _user_locks


def reset_orchestrator_for_testing() -> None:
    """Reset the cached orchestrator singleton (testing hook)."""

    global _orchestrator
    _orchestrator = None
    _user_locks.clear()
