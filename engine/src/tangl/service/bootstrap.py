from __future__ import annotations

"""Bootstrap helpers for the canonical manager-first service wiring."""

from tangl.persistence import PersistenceManager, PersistenceManagerFactory

from .service_manager import ServiceManager


def build_service_manager(
    persistence_manager: PersistenceManager | None = None,
) -> ServiceManager:
    """Build the canonical explicit service manager."""

    if persistence_manager is None:
        persistence_manager = PersistenceManagerFactory.create_persistence_manager()
    return ServiceManager(persistence_manager)

__all__ = ["build_service_manager"]
