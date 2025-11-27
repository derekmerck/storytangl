from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.rest import media_server
from tangl.story.fabula.world_bundle import WorldBundle
from tangl.story.fabula.world_loader import WorldLoader


def _media_mvp_bundle() -> WorldBundle:
    worlds_root = Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "worlds"
    loader = WorldLoader([worlds_root])
    bundles = loader.discover_bundles()
    return bundles["media_mvp"]


@pytest.fixture()
def media_client(client: TestClient) -> TestClient:  # noqa: PT004
    bundle = _media_mvp_bundle()
    media_server.mount_world_media(media_server.app, bundle.manifest.uid, bundle.media_dir)
    return client


def test_media_server_serves_files(media_client: TestClient) -> None:
    response = media_client.get("http://test/media/world/media_mvp/test_image.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert response.content


def test_media_server_missing_file_returns_404(media_client: TestClient) -> None:
    response = media_client.get("http://test/media/world/media_mvp/does_not_exist.png")

    assert response.status_code == 404
