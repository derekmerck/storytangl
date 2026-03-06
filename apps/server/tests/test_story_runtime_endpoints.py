from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.core import Selector
from tangl.rest.app import app
from tangl.rest.dependencies import get_orchestrator, reset_orchestrator_for_testing
from tangl.rest.dependencies_gateway import get_service_gateway
from tangl.service.user.user import User
from tangl.service.api_endpoint import AccessLevel
from tangl.story.episode import Action
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret
from tangl.vm.runtime.ledger import Ledger


def _write_story38_bundle(root: Path) -> str:
    world_dir = root / "story38_demo"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text(
        "\n".join(
            [
                "label: story38_demo",
                "scripts: script.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (world_dir / "script.yaml").write_text(
        "\n".join(
            [
                "label: story38_demo",
                "metadata:",
                "  title: Story38 Demo",
                "  author: Tests",
                "  start_at: intro.start",
                "scenes:",
                "  intro:",
                "    blocks:",
                "      start:",
                "        content: Start",
                "        actions:",
                "          - text: Continue",
                "            successor: end",
                "      end:",
                "        content: End",
            ]
        ),
        encoding="utf-8",
    )
    return "story38_demo"


@pytest.fixture()
def story38_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, dict[str, str], str]:
    world_label = _write_story38_bundle(tmp_path)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    reset_orchestrator_for_testing()
    orchestrator = get_orchestrator()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)
    user = User(uid=user_id)
    user.set_secret(secret)
    orchestrator.persistence.save(user)

    client = TestClient(app, base_url="http://test/api/v2/")
    headers = {"X-API-Key": key_for_secret(secret)}
    try:
        yield client, headers, world_label
    finally:
        client.close()
        reset_orchestrator_for_testing()


def test_story38_rest_envelope_flow(
    story38_client: tuple[TestClient, dict[str, str], str],
    monkeypatch,
) -> None:
    client, headers, world_label = story38_client

    create = client.post(
        "story/story38/create",
        params={"world_id": world_label, "init_mode": "EAGER"},
        headers=headers,
    )
    assert create.status_code == 200
    created = create.json()
    assert created.get("status") == "ok"
    assert isinstance(created.get("envelope"), dict)
    create_fragments = created["envelope"].get("fragments", [])
    assert isinstance(create_fragments, list)

    orchestrator = get_orchestrator()
    user_id = uuid_for_secret(settings.client.secret)
    user = orchestrator.persistence.get(user_id)
    assert user is not None
    assert user.current_ledger_id is not None
    ledger = orchestrator.persistence.get(user.current_ledger_id)
    assert ledger is not None
    start = ledger.cursor
    choice = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    choice_id = str(choice.uid)

    update = client.get("story/story38/update", headers=headers)
    assert update.status_code == 200
    envelope = update.json()
    assert isinstance(envelope.get("fragments"), list)

    captured: dict[str, object] = {}
    original_resolve = Ledger.resolve_choice

    def _capture_resolve(self, edge_id, *, choice_payload=None):
        captured["edge_id"] = edge_id
        captured["choice_payload"] = choice_payload
        return original_resolve(self, edge_id, choice_payload=choice_payload)

    monkeypatch.setattr(Ledger, "resolve_choice", _capture_resolve)

    payload = {"move": "knight", "to": "b6"}
    do = client.post(
        "story/story38/do",
        json={"uid": choice_id, "payload": payload},
        headers=headers,
    )
    assert do.status_code == 200
    post_do_envelope = do.json()
    assert isinstance(post_do_envelope.get("fragments"), list)
    assert post_do_envelope.get("step", 0) >= envelope.get("step", 0)
    assert captured.get("edge_id") == choice.uid
    assert captured.get("choice_payload") == payload

    status = client.get("story/story38/status", headers=headers)
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload.get("status") == "ok"
    assert status_payload.get("choice_steps", 0) >= 1

    drop = client.delete("story/story38/drop", headers=headers)
    assert drop.status_code == 200
    dropped = drop.json()
    assert dropped.get("status") == "ok"
    assert dropped.get("dropped_ledger_id")


def test_story38_status_returns_403_when_endpoint_is_restricted_for_non_privileged_user(
    story38_client: tuple[TestClient, dict[str, str], str],
) -> None:
    client, headers, world_label = story38_client
    create = client.post(
        "story/story38/create",
        params={"world_id": world_label, "init_mode": "EAGER"},
        headers=headers,
    )
    assert create.status_code == 200

    gateway = get_service_gateway()
    binding = gateway.orchestrator._endpoints["RuntimeController.get_story_info"]
    previous_level = binding.endpoint.access_level
    binding.endpoint.access_level = AccessLevel.RESTRICTED
    try:
        response = client.get("story/story38/status", headers=headers)
        assert response.status_code == 403
        detail = response.json().get("detail", "")
        assert "Access denied" in detail
    finally:
        binding.endpoint.access_level = previous_level
