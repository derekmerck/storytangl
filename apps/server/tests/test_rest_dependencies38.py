from __future__ import annotations

from tangl.rest.dependencies import get_orchestrator, reset_orchestrator_for_testing
from tangl.rest.dependencies38 import (
    get_service_adapter38,
    get_service_gateway38,
    reset_service_gateway38_for_testing,
)


def test_get_service_gateway38_singleton_shares_persistence() -> None:
    reset_orchestrator_for_testing()
    reset_service_gateway38_for_testing()

    orchestrator = get_orchestrator()
    gateway = get_service_gateway38()

    assert gateway is get_service_gateway38()
    assert gateway.persistence is orchestrator.persistence

    policy = gateway.orchestrator._endpoints["RuntimeController.create_story38"].policy
    assert "details.ledger" in policy.persist_paths


def test_get_service_adapter38_singleton_shares_gateway_and_persistence() -> None:
    reset_orchestrator_for_testing()
    reset_service_gateway38_for_testing()

    orchestrator = get_orchestrator()
    adapter = get_service_adapter38()
    gateway = get_service_gateway38()

    assert adapter is get_service_adapter38()
    assert adapter.gateway is gateway
    assert adapter.persistence is orchestrator.persistence
