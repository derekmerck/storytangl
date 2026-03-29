from __future__ import annotations

from tangl.rest.dependencies import get_persistence, reset_service_state_for_testing
from tangl.rest.dependencies_gateway import get_service_manager, reset_service_manager_for_testing


def test_get_service_manager_singleton_shares_persistence() -> None:
    reset_service_state_for_testing()
    reset_service_manager_for_testing()

    service_manager = get_service_manager()

    assert service_manager is get_service_manager()
    assert service_manager.persistence is get_persistence()
