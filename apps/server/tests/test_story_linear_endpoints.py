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
from conftest import extract_choices_from_fragments

LINEAR_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "linear_script.yaml"
)


@pytest.fixture()
def linear_story_client() -> tuple[TestClient, dict[str, str]]:
    reset_orchestrator_for_testing()
    World.clear_instances()

    orchestrator = get_orchestrator()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)

    user = User(uid=user_id)
    user.set_secret(secret)
    orchestrator.persistence.save(user)

    script_data = yaml.safe_load(LINEAR_SCRIPT.read_text())
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


def test_linear_story_rest_flow(linear_story_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = linear_story_client

    create = client.post("story/story/create", params={"world_id": "the_path"}, headers=headers)
    assert create.status_code == 200

    update = client.get("story/update", headers=headers)
    assert update.status_code == 200
    payload = update.json()
    fragments = payload["fragments"]
    assert _fragment_contains(fragments, "You begin your journey at dawn.")

    choices = extract_choices_from_fragments(fragments)
    assert choices, "Expected an initial choice to be available"

    first_choice = choices[0].get("uid") or choices[0].get("source_id")
    resolve_first = client.post("story/do", json={"uid": first_choice}, headers=headers)
    assert resolve_first.status_code == 200

    update_two = client.get("story/update", headers=headers)
    assert update_two.status_code == 200
    payload_two = update_two.json()
    fragments_two = payload_two["fragments"]
    assert _fragment_contains(
        fragments_two,
        "The path winds through ancient woods.",
    )

    choices_two = extract_choices_from_fragments(fragments_two)
    assert choices_two, "Expected a continuation choice after the middle block"

    second_choice = choices_two[0].get("uid") or choices_two[0].get("source_id")
    resolve_second = client.post("story/do", json={"uid": second_choice}, headers=headers)
    assert resolve_second.status_code == 200

    update_three = client.get("story/update", headers=headers)
    assert update_three.status_code == 200
    payload_three = update_three.json()
    fragments_three = payload_three["fragments"]
    assert _fragment_contains(fragments_three, "You arrive at the village.")
    assert extract_choices_from_fragments(fragments_three) == []
