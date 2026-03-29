from __future__ import annotations

from tangl.rest import dependencies
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    reset_service_manager_for_testing,
)


def test_get_persistence_singleton() -> None:
    dependencies.reset_service_state_for_testing()
    persistence = dependencies.get_persistence()

    assert persistence is dependencies.get_persistence()


def test_reset_service_state_clears_manager_cache() -> None:
    dependencies.reset_service_state_for_testing()
    reset_service_manager_for_testing()

    manager = get_service_manager()
    persistence = dependencies.get_persistence()
    assert manager.persistence is persistence

    dependencies.reset_service_state_for_testing()
    reset_service_manager_for_testing()

    next_manager = get_service_manager()
    assert next_manager is not manager
    assert next_manager.persistence is dependencies.get_persistence()
