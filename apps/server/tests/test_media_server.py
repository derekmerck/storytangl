from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from tangl.rest import media_server
from tangl.service.world_registry import WorldRegistry


def _media_mvp_bundle():
    worlds_root = Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "worlds"
    registry = WorldRegistry([worlds_root])
    return registry.bundles["media_mvp"]


@pytest.fixture()
def media_client(client: TestClient) -> TestClient:  # noqa: PT004
    bundle = _media_mvp_bundle()
    media_server.mount_world_media(media_server.app, bundle.manifest.label, bundle.media_dir)
    return client


def test_media_server_serves_files(media_client: TestClient) -> None:
    response = media_client.get("http://test/media/world/media_mvp/test_image.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert response.content


def test_media_server_missing_file_returns_404(media_client: TestClient) -> None:
    response = media_client.get("http://test/media/world/media_mvp/does_not_exist.png")

    assert response.status_code == 404


def test_story_media_server_serves_story_scoped_files(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    story_root = tmp_path / "story_media"
    story_dir = story_root / "story-1"
    story_dir.mkdir(parents=True)
    (story_dir / "avatar.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        media_server,
        "get_story_media_dir",
        lambda story_id=None: story_root if story_id is None else story_root / str(story_id),
    )

    response = client.get("http://test/media/story/story-1/avatar.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_story_media_server_rejects_path_traversal(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    story_root = tmp_path / "story_media"
    story_dir = story_root / "story-1"
    story_dir.mkdir(parents=True)
    (story_root / "escape.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"></svg>',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        media_server,
        "get_story_media_dir",
        lambda story_id=None: story_root if story_id is None else story_root / str(story_id),
    )

    response = client.get("http://test/media/story/story-1/%2e%2e/escape.svg")

    assert response.status_code == 404


def test_story_media_server_rejects_story_root_outside_global_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    story_root = tmp_path / "story_media"
    story_root.mkdir(parents=True)
    outside_story_dir = tmp_path / "outside" / "story-1"
    outside_story_dir.mkdir(parents=True)
    (outside_story_dir / "avatar.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"></svg>',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        media_server,
        "get_story_media_dir",
        lambda story_id=None: story_root if story_id is None else outside_story_dir,
    )

    with pytest.raises(HTTPException, match="Story media not configured"):
        media_server._resolve_safe_story_media_path("story-1", "avatar.svg")
