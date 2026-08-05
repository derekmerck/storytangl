"""Public recovery-secret transport contracts."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tangl.rest.app import app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import reset_service_manager_for_testing


@pytest.fixture()
def client() -> Iterator[TestClient]:
    reset_service_state_for_testing()
    reset_service_manager_for_testing()
    test_client = TestClient(app, base_url="http://test/api/v2/")
    try:
        yield test_client
    finally:
        test_client.close()
        reset_service_manager_for_testing()
        reset_service_state_for_testing()


def test_create_user_restores_one_user_for_a_recovery_secret(client: TestClient) -> None:
    first = client.post("user/create", params={"secret": "recovery-secret"})
    second = client.post("user/create", params={"secret": "recovery-secret"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user_id"] == second.json()["user_id"]


def test_secret_rotation_rejects_another_players_recovery_secret(client: TestClient) -> None:
    first = client.post("user/create", params={"secret": "first-secret"})
    second = client.post("user/create", params={"secret": "second-secret"})
    assert first.status_code == 200
    assert second.status_code == 200

    conflict = client.put(
        "user/secret",
        params={"secret": "second-secret"},
        headers={"X-API-Key": first.json()["api_key"]},
    )
    no_op = client.put(
        "user/secret",
        params={"secret": "first-secret"},
        headers={"X-API-Key": first.json()["api_key"]},
    )

    assert conflict.status_code == 409
    assert no_op.status_code == 200
    assert no_op.json()["user_id"] == first.json()["user_id"]
