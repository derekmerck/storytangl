"""Shared FastAPI dependencies for the StoryTangl REST app."""

from __future__ import annotations

from tangl.persistence import PersistenceManager, PersistenceManagerFactory

_persistence: PersistenceManager | None = None


def get_persistence() -> PersistenceManager:
    """Return the process-wide persistence manager shared by transports."""

    global _persistence
    if _persistence is None:
        _persistence = PersistenceManagerFactory.create_persistence_manager()
    return _persistence


def reset_service_state_for_testing() -> None:
    """Reset shared REST transport state used by service-manager dependencies."""

    global _persistence
    _persistence = None
    from tangl.rest.dependencies_gateway import reset_service_manager_for_testing

    reset_service_manager_for_testing()
