"""HTTP smoke coverage for the Hall Monitor credentials worked vertical."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.media.media_resource import MediaDep
from tangl.media.media_resource.media_resource_inv_tag import MediaRITStatus
from tangl.rest.app import app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    reset_service_manager_for_testing,
)
from tangl.service.user.user import User
from tangl.service.world_registry import resolve_world
from tangl.story import InitMode
from tangl.story.fabula.world import World
from tangl.story.story_graph import StoryGraph
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _choice_id(payload: dict[str, object], text: str) -> str:
    fragments = payload["fragments"]
    assert isinstance(fragments, list)
    for fragment in reversed(fragments):
        if isinstance(fragment, dict) and fragment.get("fragment_type") == "choice":
            if fragment.get("text") == text:
                edge_id = fragment.get("edge_id")
                assert isinstance(edge_id, str)
                return edge_id
    raise AssertionError(f"No {text!r} choice in {fragments!r}")


def _fragments(payload: dict[str, object], fragment_type: str) -> list[dict[str, object]]:
    """Return one response's client-visible fragments of ``fragment_type``."""

    fragments = payload["fragments"]
    assert isinstance(fragments, list)
    return [
        fragment
        for fragment in fragments
        if isinstance(fragment, dict) and fragment.get("fragment_type") == fragment_type
    ]


@pytest.fixture()
def hall_monitor_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, dict[str, str]]]:
    """Serve the compiled repository Hall Monitor world through FastAPI."""

    monkeypatch.setattr("tangl.utils.shelved2.SHELVED_CACHE_ENABLED", False)
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


def test_hall_monitor_delivers_subject_mismatch_card_without_hidden_truth(
    hall_monitor_client: tuple[TestClient, dict[str, str]],
) -> None:
    """The public next frontier compares the live bearer with the bound ID portrait."""

    client, headers = hall_monitor_client
    created = client.post(
        "story/story/create",
        params={"world_id": "hall_monitor", "init_mode": "EAGER"},
        headers=headers,
    )
    entered = client.post(
        "story/do",
        json={"edge_id": _choice_id(created.json(), "Monitor the morning halls")},
        headers=headers,
    )
    inspected = client.post(
        "story/do",
        json={
            "edge_id": _choice_id(entered.json(), "Inspect a document"),
            "payload": {"piece_ids": ["0:doctor's note"]},
        },
        headers=headers,
    )
    advanced = client.post(
        "story/do",
        json={"edge_id": _choice_id(inspected.json(), "Send back to class")},
        headers=headers,
    )

    assert advanced.status_code == 200
    payload = advanced.json()
    text = json.dumps(payload)
    candidate = next(
        fragment
        for fragment in _fragments(payload, "piece")
        if fragment.get("content") == "Rowan Vale"
    )
    identity = next(
        fragment
        for fragment in _fragments(payload, "piece")
        if fragment.get("hints", {}).get("label_text") == "student ID"
    )
    media = _fragments(payload, "media")
    relation = next(
        fragment
        for fragment in _fragments(payload, "group")
        if fragment.get("group_type") == "piece_media"
    )

    assert candidate["properties"]["look_description"] == "with red hair"
    assert identity["properties"]["look_description"] == "with blonde hair"
    assert len(media) == 1
    assert media[0]["media_role"] == "credential_card"
    assert isinstance(media[0].get("url"), str)
    assert relation["member_ids"] == [identity["uid"], media[0]["uid"]]
    assert "correct_disposition" not in text
    assert "subject_mismatch" not in text

    reloaded = client.get("story/update", headers=headers)
    assert reloaded.status_code == 200
    reloaded_media = _fragments(reloaded.json(), "media")
    assert [fragment["uid"] for fragment in reloaded_media] == [media[0]["uid"]]


def test_hall_monitor_keeps_the_text_floor_when_card_becomes_pending(
    hall_monitor_client: tuple[TestClient, dict[str, str]],
) -> None:
    """A real service response omits unavailable card media without losing its papers."""

    client, headers = hall_monitor_client
    created = client.post(
        "story/story/create",
        params={"world_id": "hall_monitor", "init_mode": "EAGER"},
        headers=headers,
    )
    entered = client.post(
        "story/do",
        json={"edge_id": _choice_id(created.json(), "Monitor the morning halls")},
        headers=headers,
    )
    inspected = client.post(
        "story/do",
        json={
            "edge_id": _choice_id(entered.json(), "Inspect a document"),
            "payload": {"piece_ids": ["0:doctor's note"]},
        },
        headers=headers,
    )
    advanced = client.post(
        "story/do",
        json={"edge_id": _choice_id(inspected.json(), "Send back to class")},
        headers=headers,
    )
    identity = next(
        fragment
        for fragment in _fragments(advanced.json(), "piece")
        if fragment.get("hints", {}).get("label_text") == "student ID"
    )

    service_manager = get_service_manager()
    with service_manager.open_session(
        user_id=uuid_for_secret(settings.client.secret),
        write_back=True,
    ) as session:
        card = next(
            dependency
            for dependency in session.ledger.graph.values()
            if isinstance(dependency, MediaDep)
            and dependency.label == "credential-card-card"
            and dependency.provider is not None
        )
        card.provider.status = MediaRITStatus.PENDING

    inspected_pending = client.post(
        "story/do",
        json={
            "edge_id": _choice_id(advanced.json(), "Inspect a document"),
            "payload": {"piece_ids": [identity["piece_id"]]},
        },
        headers=headers,
    )

    assert inspected_pending.status_code == 200, inspected_pending.json()
    payload = inspected_pending.json()
    assert "Rowan Vale" in json.dumps(payload)
    assert any(
        fragment.get("hints", {}).get("label_text") == "student ID"
        for fragment in _fragments(payload, "piece")
    )
    assert _fragments(payload, "media") == []
    assert not any(
        fragment.get("group_type") == "piece_media"
        for fragment in _fragments(payload, "group")
    )


def test_hall_monitor_world_resolution_reuses_until_service_reset(
    hall_monitor_client: tuple[TestClient, dict[str, str]],
) -> None:
    """A reset recompiles and registers worlds used by persisted story graphs."""

    _client, _headers = hall_monitor_client
    first = resolve_world("hall_monitor")
    assert resolve_world("hall_monitor") is first
    graph_payload = first.create_story(
        "hall_monitor",
        init_mode=InitMode.EAGER,
    ).graph.unstructure()

    reset_service_state_for_testing()
    World.clear_instances()

    second = resolve_world("hall_monitor")
    assert second is not first
    assert World.get_instance("hall_monitor") is second

    restored = StoryGraph.structure(graph_payload)
    assert restored.world is second
