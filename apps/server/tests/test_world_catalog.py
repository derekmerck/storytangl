"""Discovered author metadata through Service and the top-level REST app."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.persistence import PersistenceManagerFactory
from tangl.rest import dependencies, dependencies_gateway
from tangl.rest.app import app
from tangl.service import ServiceManager, user_id_by_key
from tangl.service import world_registry
from tangl.utils.hash_secret import key_for_secret


@pytest.fixture
def catalog_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ServiceManager:
    authors = {
        "collaborative": ["Ada", "Grace"],
        "solo": "Ursula",
        "anonymous": None,
    }
    for label, author in authors.items():
        bundle = tmp_path / label
        bundle.mkdir()
        metadata = {"title": label.title()}
        if author is not None:
            metadata["author"] = author
        (bundle / "world.yaml").write_text(
            yaml.safe_dump({"label": label, "scripts": "script.yaml", "metadata": metadata}),
            encoding="utf-8",
        )
        (bundle / "script.yaml").write_text("label: " + label + "\n", encoding="utf-8")

    # Restore existing process state through monkeypatch, without clearing live registries.
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [tmp_path])
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "users")
    monkeypatch.setattr(dependencies, "_persistence", persistence)
    monkeypatch.setattr(dependencies_gateway, "_service_manager", None)
    return dependencies_gateway.get_service_manager()


EXPECTED_AUTHORS = {
    "collaborative": ["Ada", "Grace"],
    "solo": "Ursula",
    "anonymous": "Unknown",
}


def test_service_discovered_world_authors(catalog_manager: ServiceManager) -> None:
    worlds = catalog_manager.list_worlds()

    assert {world.label: world.author for world in worlds} == EXPECTED_AUTHORS


def test_top_level_rest_discovered_world_authors(catalog_manager: ServiceManager) -> None:
    api_key = key_for_secret(settings.client.secret)
    assert user_id_by_key(api_key, catalog_manager.persistence) is None

    with TestClient(app) as client:
        # Startup must use the isolated persistence, through the real app lifespan.
        assert user_id_by_key(api_key, catalog_manager.persistence) is not None
        response = client.get("/api/v2/system/worlds")

    assert response.status_code == 200
    assert {world["label"]: world["author"] for world in response.json()} == EXPECTED_AUTHORS
