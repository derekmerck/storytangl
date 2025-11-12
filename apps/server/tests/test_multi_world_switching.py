"""Test story reset and multi-world switching behavior via REST API."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
import yaml
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.rest.app import app
from tangl.rest.dependencies import get_orchestrator, reset_orchestrator_for_testing
from tangl.service.user.user import User
from tangl.story.fabula.world import World
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret


DEMO_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "engine"
    / "tests"
    / "resources"
    / "demo_script.yaml"
)

LINEAR_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "engine"
    / "tests"
    / "resources"
    / "linear_script.yaml"
)


@pytest.fixture()
def multi_world_client() -> tuple[TestClient, dict[str, str], UUID]:
    reset_orchestrator_for_testing()
    World.clear_instances()

    orchestrator = get_orchestrator()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)

    user = User(uid=user_id)
    user.set_secret(secret)
    orchestrator.persistence.save(user)

    demo_data = yaml.safe_load(DEMO_SCRIPT.read_text())
    orchestrator.execute("WorldController.load_world", script_data=demo_data)

    linear_data = yaml.safe_load(LINEAR_SCRIPT.read_text())
    orchestrator.execute("WorldController.load_world", script_data=linear_data)

    client = TestClient(app, base_url="http://test/api/v2/")
    headers = {"X-API-Key": key_for_secret(secret)}

    try:
        yield client, headers, user_id
    finally:
        client.close()
        World.clear_instances()
        reset_orchestrator_for_testing()


def _fragment_contains(fragments: list[dict[str, object]], text: str) -> bool:
    return any(text in str(fragment.get("content", "")) for fragment in fragments)


def test_drop_story_without_active_story_returns_400(
    multi_world_client: tuple[TestClient, dict[str, str], UUID]
) -> None:
    client, headers, _ = multi_world_client

    response = client.delete("story/drop", headers=headers)
    assert response.status_code == 400
    assert "no active story" in response.json()["detail"].lower()


def test_drop_story_archive_preserves_ledger(
    multi_world_client: tuple[TestClient, dict[str, str], UUID]
) -> None:
    client, headers, user_id = multi_world_client
    orchestrator = get_orchestrator()

    create_resp = client.post(
        "story/story/create",
        params={"world_id": "the_crossroads"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    ledger_id = create_resp.json()["ledger_id"]

    drop_resp = client.delete(
        "story/drop",
        params={"archive": True},
        headers=headers,
    )
    assert drop_resp.status_code == 200
    payload = drop_resp.json()
    assert payload["status"] == "dropped"
    assert payload["archived"] is True
    assert payload["dropped_ledger_id"] == ledger_id
    assert "persistence_deleted" not in payload

    user = orchestrator.persistence[user_id]
    assert user.current_ledger_id is None

    archived_ledger = orchestrator.persistence.get(UUID(ledger_id))
    assert archived_ledger is not None


def test_drop_story_without_archive_deletes_ledger(
    multi_world_client: tuple[TestClient, dict[str, str], UUID]
) -> None:
    client, headers, user_id = multi_world_client
    orchestrator = get_orchestrator()

    create_resp = client.post(
        "story/story/create",
        params={"world_id": "the_crossroads"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    ledger_id = create_resp.json()["ledger_id"]

    drop_resp = client.delete("story/drop", headers=headers)
    assert drop_resp.status_code == 200
    payload = drop_resp.json()
    assert payload["archived"] is False
    assert payload.get("persistence_deleted") is True

    user = orchestrator.persistence[user_id]
    assert user.current_ledger_id is None

    with pytest.raises(KeyError):
        orchestrator.persistence[UUID(ledger_id)]


def test_multi_world_switching_flow(
    multi_world_client: tuple[TestClient, dict[str, str], UUID]
) -> None:
    client, headers, user_id = multi_world_client
    orchestrator = get_orchestrator()

    create_demo = client.post(
        "story/story/create",
        params={"world_id": "the_crossroads"},
        headers=headers,
    )
    assert create_demo.status_code == 200
    demo_ledger_id = create_demo.json()["ledger_id"]

    update_one = client.get("story/update", headers=headers)
    assert update_one.status_code == 200
    payload_one = update_one.json()
    assert _fragment_contains(payload_one["fragments"], "crossroads")
    assert len(payload_one["choices"]) >= 2

    status_before = client.get("story/status", headers=headers)
    assert status_before.status_code == 200
    step_before = status_before.json()["step"]

    first_choice = payload_one["choices"][0]["uid"]
    choose_resp = client.post("story/do", json={"uid": first_choice}, headers=headers)
    assert choose_resp.status_code == 200

    status_after = client.get("story/status", headers=headers)
    assert status_after.status_code == 200
    assert status_after.json()["step"] > step_before

    update_two = client.get("story/update", headers=headers)
    assert update_two.status_code == 200
    payload_two = update_two.json()
    assert payload_two["fragments"]

    drop_demo = client.delete(
        "story/drop",
        params={"archive": True},
        headers=headers,
    )
    assert drop_demo.status_code == 200
    assert drop_demo.json()["dropped_ledger_id"] == demo_ledger_id

    user = orchestrator.persistence[user_id]
    assert user.current_ledger_id is None

    create_linear = client.post(
        "story/story/create",
        params={"world_id": "the_path"},
        headers=headers,
    )
    assert create_linear.status_code == 200
    linear_ledger_id = create_linear.json()["ledger_id"]
    assert linear_ledger_id != demo_ledger_id

    update_three = client.get("story/update", headers=headers)
    assert update_three.status_code == 200
    payload_three = update_three.json()
    assert _fragment_contains(payload_three["fragments"], "journey at dawn")
    assert len(payload_three["choices"]) == 1

    continue_choice = payload_three["choices"][0]["uid"]
    continue_resp = client.post("story/do", json={"uid": continue_choice}, headers=headers)
    assert continue_resp.status_code == 200

    update_four = client.get("story/update", headers=headers)
    assert update_four.status_code == 200
    payload_four = update_four.json()
    assert _fragment_contains(payload_four["fragments"], "ancient woods")

    drop_linear = client.delete("story/drop", headers=headers)
    assert drop_linear.status_code == 200
    drop_linear_payload = drop_linear.json()
    assert drop_linear_payload["dropped_ledger_id"] == linear_ledger_id
    assert drop_linear_payload.get("persistence_deleted") is True

    recreate_demo = client.post(
        "story/story/create",
        params={"world_id": "the_crossroads"},
        headers=headers,
    )
    assert recreate_demo.status_code == 200
    new_demo_ledger = recreate_demo.json()["ledger_id"]
    assert new_demo_ledger not in {demo_ledger_id, linear_ledger_id}

    final_update = client.get("story/update", headers=headers)
    assert final_update.status_code == 200
    final_payload = final_update.json()
    assert _fragment_contains(final_payload["fragments"], "crossroads")
