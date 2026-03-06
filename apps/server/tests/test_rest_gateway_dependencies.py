from __future__ import annotations

from tangl.rest.dependencies import get_orchestrator, reset_orchestrator_for_testing
from tangl.rest.dependencies_gateway import (
    get_service_adapter,
    get_service_gateway,
    reset_service_gateway_for_testing,
)


def test_get_service_gateway_singleton_shares_persistence() -> None:
    reset_orchestrator_for_testing()
    reset_service_gateway_for_testing()

    orchestrator = get_orchestrator()
    gateway = get_service_gateway()

    assert gateway is get_service_gateway()
    assert gateway.persistence is orchestrator.persistence

    policy = gateway.orchestrator._endpoints["RuntimeController.create_story"].policy
    assert "details.ledger" in policy.persist_paths


def test_get_service_adapter_singleton_shares_gateway_and_persistence() -> None:
    reset_orchestrator_for_testing()
    reset_service_gateway_for_testing()

    orchestrator = get_orchestrator()
    adapter = get_service_adapter()
    gateway = get_service_gateway()

    assert adapter is get_service_adapter()
    assert adapter.gateway is gateway
    assert adapter.persistence is orchestrator.persistence
