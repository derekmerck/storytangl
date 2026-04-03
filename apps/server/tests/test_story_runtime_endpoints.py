from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.core import Selector
from tangl.rest.app import app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    reset_service_manager_for_testing,
)
from tangl.service import ServiceAccess
from tangl.service.service_method import get_service_method_spec
from tangl.service.user.user import User
from tangl.story.fabula.world import World
from tangl.story.episode import Action
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret
from tangl.vm.runtime.ledger import Ledger


def _write_story_bundle(root: Path, *, with_projector: bool = False) -> str:
    world_dir = root / "story_demo"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text(
        "\n".join(
            [
                "label: story_demo",
                "scripts: script.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (world_dir / "script.yaml").write_text(
        "\n".join(
            [
                "label: story_demo",
                "metadata:",
                "  title: Story Demo",
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
    if with_projector:
        (world_dir / "domain").mkdir()
        package_dir = world_dir / "story_demo"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "domain.py").write_text(
            "\n".join(
                [
                    "from tangl.service import KvListValue, ProjectedKVItem, ProjectedSection, ProjectedState",
                    "",
                    "class DemoProjector:",
                    "    def project(self, *, ledger):",
                    "        return ProjectedState(",
                    "            sections=[",
                    "                ProjectedSection(",
                    '                    section_id="world_state",',
                    '                    title="World State",',
                    '                    kind="mystery",',
                    "                    value=KvListValue(",
                    "                        items=[",
                    '                            ProjectedKVItem(key="Mood", value="tense"),',
                    '                            ProjectedKVItem(key="Step Seen", value=ledger.step),',
                    "                        ]",
                    "                    ),",
                    "                )",
                    "            ]",
                    "        )",
                    "",
                    "def get_story_info_projector():",
                    "    return DemoProjector()",
                ]
            ),
            encoding="utf-8",
        )
    return "story_demo"


def _session_value(payload: dict[str, object], key: str) -> object | None:
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return None

    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != "session":
            continue
        value = section.get("value")
        if not isinstance(value, dict) or value.get("value_type") != "kv_list":
            continue
        items = value.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("key") == key:
                return item.get("value")
    return None


@pytest.fixture()
def story_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, dict[str, str], str]:
    world_label = _write_story_bundle(tmp_path)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    reset_service_state_for_testing()
    reset_service_manager_for_testing()
    World.clear_instances()
    service_manager = get_service_manager()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)
    user = User(uid=user_id)
    user.set_secret(secret)
    service_manager.persistence.save(user)

    client = TestClient(app, base_url="http://test/api/v2/")
    headers = {"X-API-Key": key_for_secret(secret)}
    try:
        yield client, headers, world_label
    finally:
        client.close()
        World.clear_instances()
        reset_service_manager_for_testing()
        reset_service_state_for_testing()


def test_story_rest_envelope_flow(
    story_client: tuple[TestClient, dict[str, str], str],
    monkeypatch,
) -> None:
    client, headers, world_label = story_client

    create = client.post(
        "story/story/create",
        params={"world_id": world_label, "init_mode": "EAGER"},
        headers=headers,
    )
    assert create.status_code == 200
    created = create.json()
    assert isinstance(created.get("fragments"), list)
    create_fragments = created.get("fragments", [])
    assert isinstance(create_fragments, list)

    service_manager = get_service_manager()
    user_id = uuid_for_secret(settings.client.secret)
    user = service_manager.persistence.get(user_id)
    assert user is not None
    assert user.current_ledger_id is not None
    ledger = service_manager.persistence.get(user.current_ledger_id)
    assert ledger is not None
    start = ledger.cursor
    choice = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    choice_id = str(choice.uid)

    update = client.get("story/update", headers=headers)
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
        "story/do",
        json={"choice_id": choice_id, "payload": payload},
        headers=headers,
    )
    assert do.status_code == 200
    post_do_envelope = do.json()
    assert isinstance(post_do_envelope.get("fragments"), list)
    assert post_do_envelope.get("step", 0) >= envelope.get("step", 0)
    assert captured.get("edge_id") == choice.uid
    assert captured.get("choice_payload") == payload

    status = client.get("story/info", headers=headers)
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload.get("sections")
    step_value = _session_value(status_payload, "Step")
    assert isinstance(step_value, int)
    assert step_value >= post_do_envelope.get("step", 0)

    drop = client.delete("story/drop", headers=headers)
    assert drop.status_code == 200
    dropped = drop.json()
    assert dropped.get("status") == "ok"
    assert dropped.get("dropped_ledger_id")


def test_story_info_returns_403_when_endpoint_is_restricted_for_non_privileged_user(
    story_client: tuple[TestClient, dict[str, str], str],
) -> None:
    from dataclasses import replace

    client, headers, world_label = story_client
    create = client.post(
        "story/story/create",
        params={"world_id": world_label, "init_mode": "EAGER"},
        headers=headers,
    )
    assert create.status_code == 200

    service_manager = get_service_manager()
    method = service_manager.get_story_info.__func__
    previous_spec = get_service_method_spec(method)
    assert previous_spec is not None
    setattr(
        method,
        "_service_method_spec",
        replace(previous_spec, access=ServiceAccess.DEV),
    )
    try:
        response = client.get("story/info", headers=headers)
        assert response.status_code == 403
        detail = response.json().get("detail", "")
        assert "Access denied" in detail
    finally:
        setattr(method, "_service_method_spec", previous_spec)


def test_story_info_returns_world_authored_projected_sections(
    tmp_path: Path,
    monkeypatch,
) -> None:
    world_label = _write_story_bundle(tmp_path, with_projector=True)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    reset_service_state_for_testing()
    reset_service_manager_for_testing()
    World.clear_instances()
    secret = settings.client.secret
    user_id = uuid_for_secret(secret)
    service_manager = get_service_manager()
    user = User(uid=user_id)
    user.set_secret(secret)
    service_manager.persistence.save(user)

    client = TestClient(app, base_url="http://test/api/v2/")
    headers = {"X-API-Key": key_for_secret(secret)}
    try:
        create = client.post(
            "story/story/create",
            params={"world_id": world_label, "init_mode": "EAGER"},
            headers=headers,
        )
        assert create.status_code == 200

        response = client.get("story/info", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        sections = payload.get("sections")
        assert isinstance(sections, list)
        assert sections[0]["section_id"] == "world_state"
        assert sections[0]["kind"] == "mystery"
        assert sections[0]["value"]["items"][0]["key"] == "Mood"
        assert sections[0]["value"]["items"][0]["value"] == "tense"
    finally:
        client.close()
        World.clear_instances()
        reset_service_manager_for_testing()
        reset_service_state_for_testing()
