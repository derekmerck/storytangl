from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.rest.app import app
from tangl.rest.dependencies import get_orchestrator, reset_orchestrator_for_testing
from tangl.service.user.user import User
from tangl.story.fabula.world import World
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret


BRANCHING_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "demo_script.yaml"
)


@pytest.fixture()
def branching_story_client() -> tuple[TestClient, dict[str, str]]:
    reset_orchestrator_for_testing()
    World.clear_instances()

    orchestrator = get_orchestrator()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)

    user = User(uid=user_id)
    user.set_secret(secret)
    orchestrator.persistence.save(user)

    script_data = yaml.safe_load(BRANCHING_SCRIPT.read_text())
    orchestrator.execute("WorldController.load_world", script_data=script_data)

    client = TestClient(app, base_url="http://test/api/v2/")
    headers = {"X-API-Key": key_for_secret(secret)}

    try:
        yield client, headers
    finally:
        client.close()
        World.clear_instances()
        reset_orchestrator_for_testing()


def _fragment_contains(fragments: list[dict[str, object]], text: str) -> bool:
    return any(text in str(fragment.get("content", "")) for fragment in fragments)


def _find_choice(choices: list[dict[str, object]], keyword: str) -> dict[str, object]:
    for choice in choices:
        if keyword.lower() in str(choice.get("label", "")).lower():
            return choice
    raise AssertionError(f"Choice containing '{keyword}' not found: {choices}")


def test_branching_story_left_path_rest(branching_story_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = branching_story_client

    create = client.post("story/story/create", params={"world_id": "the_crossroads"}, headers=headers)
    assert create.status_code == 200

    update = client.get("story/update", headers=headers)
    assert update.status_code == 200
    payload = update.json()

    assert _fragment_contains(payload["fragments"], "You stand at a crossroads in the forest.")
    assert len(payload["choices"]) == 3

    left_choice = _find_choice(payload["choices"], "left")
    resolve_left = client.post("story/do", json={"uid": left_choice["uid"]}, headers=headers)
    assert resolve_left.status_code == 200

    update_two = client.get("story/update", headers=headers)
    assert update_two.status_code == 200
    payload_two = update_two.json()

    assert _fragment_contains(payload_two["fragments"], "peaceful garden")
    assert payload_two["choices"] == []


def test_branching_story_enter_cave_rest(branching_story_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = branching_story_client

    client.post("story/story/create", params={"world_id": "the_crossroads"}, headers=headers)

    first_update = client.get("story/update", headers=headers)
    payload = first_update.json()

    right_choice = _find_choice(payload["choices"], "right")
    resolve_right = client.post("story/do", json={"uid": right_choice["uid"]}, headers=headers)
    assert resolve_right.status_code == 200

    second_update = client.get("story/update", headers=headers)
    payload_two = second_update.json()

    assert _fragment_contains(payload_two["fragments"], "dark cave")
    assert len(payload_two["choices"]) == 2
    assert _find_choice(payload_two["choices"], "enter")
    assert _find_choice(payload_two["choices"], "back")

    enter_choice = _find_choice(payload_two["choices"], "enter")
    resolve_enter = client.post("story/do", json={"uid": enter_choice["uid"]}, headers=headers)
    assert resolve_enter.status_code == 200

    third_update = client.get("story/update", headers=headers)
    payload_three = third_update.json()

    assert _fragment_contains(payload_three["fragments"], "deeper than you thought")
    assert payload_three["choices"] == []


def test_branching_story_backtrack_rest(branching_story_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = branching_story_client

    client.post("story/story/create", params={"world_id": "the_crossroads"}, headers=headers)

    first_update = client.get("story/update", headers=headers).json()
    right_choice = _find_choice(first_update["choices"], "right")
    client.post("story/do", json={"uid": right_choice["uid"]}, headers=headers)

    second_update = client.get("story/update", headers=headers).json()
    back_choice = _find_choice(second_update["choices"], "back")
    resolve_back = client.post("story/do", json={"uid": back_choice["uid"]}, headers=headers)
    assert resolve_back.status_code == 200

    third_update = client.get("story/update", headers=headers)
    assert third_update.status_code == 200
    payload_three = third_update.json()

    assert _fragment_contains(payload_three["fragments"], "You stand at a crossroads in the forest.")
    assert payload_three["choices"] == []
