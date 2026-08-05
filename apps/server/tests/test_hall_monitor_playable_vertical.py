"""HTTP smoke coverage for the Hall Monitor credentials worked vertical."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.rest.app import app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    reset_service_manager_for_testing,
)
from tangl.service.user.user import User
from tangl.service.world_registry import resolve_world
from tangl.story.fabula.world import World
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _choice_id(payload: dict[str, object], text: str) -> str:
    fragments = payload["fragments"]
    assert isinstance(fragments, list)
    for fragment in fragments:
        if isinstance(fragment, dict) and fragment.get("fragment_type") == "choice":
            if fragment.get("text") == text:
                edge_id = fragment.get("edge_id")
                assert isinstance(edge_id, str)
                return edge_id
    raise AssertionError(f"No {text!r} choice in {fragments!r}")


@pytest.fixture()
def hall_monitor_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, dict[str, str]]]:
    """Serve the compiled repository Hall Monitor world through FastAPI."""

    monkeypatch.setattr(
        "tangl.service.world_registry.get_world_dirs",
        lambda: [_repo_worlds_dir()],
    )
    reset_service_state_for_testing()
    reset_service_manager_for_testing()
    World.clear_instances()

    service_manager = get_service_manager()
    secret = settings.client.secret
    user = User(uid=uuid_for_secret(secret))
    user.set_secret(secret)
    service_manager.persistence.save(user)

    client = TestClient(app, base_url="http://test/api/v2/")
    try:
        yield client, {"X-API-Key": key_for_secret(secret)}
    finally:
        client.close()
        World.clear_instances()
        reset_service_manager_for_testing()
        reset_service_state_for_testing()


def test_hall_monitor_inspection_survives_http_session_reload(
    hall_monitor_client: tuple[TestClient, dict[str, str]],
) -> None:
    """The public HTTP transcript retains its text floor after credential inspection."""

    client, headers = hall_monitor_client
    created = client.post(
        "story/story/create",
        params={"world_id": "hall_monitor", "init_mode": "EAGER"},
        headers=headers,
    )
    assert created.status_code == 200
    assert _choice_id(created.json(), "Monitor the morning halls")

    entered = client.post(
        "story/do",
        json={"edge_id": _choice_id(created.json(), "Monitor the morning halls")},
        headers=headers,
    )
    assert entered.status_code == 200
    entered_payload = entered.json()
    entered_text = json.dumps(entered_payload)
    assert "Mira Quill steps forward." in entered_text
    assert "doctor's note" in entered_text
    assert "correct_disposition" not in entered_text

    inspected = client.post(
        "story/do",
        json={
            "edge_id": _choice_id(entered_payload, "Inspect a document"),
            "payload": {"piece_ids": ["0:doctor's note"]},
        },
        headers=headers,
    )
    assert inspected.status_code == 200
    inspected_text = json.dumps(inspected.json())
    assert "The required nurse signature is missing." in inspected_text
    assert "Send back to class" in inspected_text
    assert "correct_disposition" not in inspected_text

    denied = client.post(
        "story/do",
        json={"edge_id": _choice_id(inspected.json(), "Send back to class")},
        headers=headers,
    )
    assert denied.status_code == 200

    reloaded = client.get("story/update", headers=headers)
    assert reloaded.status_code == 200
    reloaded_text = json.dumps(reloaded.json())
    assert "Mira Quill steps forward." in reloaded_text
    assert "The required nurse signature is missing." in reloaded_text


def test_hall_monitor_world_resolution_reuses_the_compiled_world(
    hall_monitor_client: tuple[TestClient, dict[str, str]],
) -> None:
    """Repeated service lookups keep one compiled singleton world per directory set."""

    _client, _headers = hall_monitor_client

    assert resolve_world("hall_monitor") is resolve_world("hall_monitor")
