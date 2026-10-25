from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock
import wave

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
import yaml

from tangl.core import Registry
from tangl.loaders import WorldCompiler
from tangl.persistence import PersistenceManagerFactory
from tangl.rest import dependencies, dependencies_gateway, media_server
from tangl.rest.app import app
from tangl.service import world_registry
from tangl.service.world_registry import WorldRegistry
from tangl.story import World


@pytest.fixture
def startup_media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for label, media_dir in (("startup_media", "assets"), ("other_media", "media")):
        bundle = tmp_path / label
        assets = bundle / media_dir / "nested"
        assets.mkdir(parents=True)
        (bundle / "world.yaml").write_text(
            yaml.safe_dump({"label": label, "media_dir": media_dir}), encoding="utf-8"
        )
        (bundle / "script.yaml").write_text(
            "metadata:\n"
            f"  title: {label}\n"
            "  start_at: intro.start\n"
            "scenes:\n"
            "  intro:\n"
            "    blocks:\n"
            "      start:\n"
            "        content: An image.\n"
            "        media:\n"
            "          - name: nested/picture.svg\n"
            "            media_role: narrative_im\n",
            encoding="utf-8",
        )
        (assets / "picture.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
            '<rect width="8" height="8" fill="blue"/></svg>',
            encoding="utf-8",
        )
        with wave.open(str(assets / "tone.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(b"\x00\x00" * 80)

    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [tmp_path])
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    monkeypatch.setattr(World, "_instances", Registry())
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "users")
    monkeypatch.setattr(dependencies, "_persistence", persistence)
    monkeypatch.setattr(dependencies_gateway, "_service_manager", None)
    monkeypatch.setattr(dependencies_gateway, "_api_key_index", {})
    monkeypatch.setattr(media_server.app.router, "routes", list(media_server.app.router.routes))
    return tmp_path


def test_top_level_startup_serves_discovered_media_without_compiling(
    startup_media: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compile_world = Mock(side_effect=AssertionError("Startup must not compile worlds"))
    monkeypatch.setattr(WorldCompiler, "compile", compile_world)
    for _ in range(2):
        with TestClient(app) as client:
            for label, directory in (("startup_media", "assets"), ("other_media", "media")):
                for filename, mime_types in (
                    ("picture.svg", {"image/svg+xml"}),
                    ("tone.wav", {"audio/wav", "audio/x-wav", "audio/vnd.wave"}),
                ):
                    response = client.get(f"/media/world/{label}/nested/{filename}")
                    assert response.status_code == 200
                    assert response.headers["content-type"] in mime_types
                    assert response.content == (
                        startup_media / label / directory / "nested" / filename
                    ).read_bytes()
                assert client.get(f"/media/world/{label}/missing.svg").status_code == 404
                mounts = [
                    route for route in media_server.app.routes if route.path == f"/world/{label}"
                ]
                assert len(mounts) == 1
    compile_world.assert_not_called()


def test_rest_story_media_url_is_fetchable_after_startup(startup_media: Path) -> None:
    with TestClient(app) as client:
        registered = client.post("/api/v2/user/create")
        assert registered.status_code == 200
        user = registered.json()
        response = client.post(
            "/api/v2/story/create",
            params={"world_id": "startup_media", "init_mode": "EAGER"},
            headers={"X-API-Key": user["api_key"]},
        )
        assert response.status_code == 200
        fragment = next(item for item in response.json()["fragments"] if item.get("url"))
        assert fragment["url"] == "/media/world/startup_media/nested/picture.svg"
        asset = client.get(fragment["url"])
        assert asset.status_code == 200
        assert asset.content == (
            startup_media / "startup_media/assets/nested/picture.svg"
        ).read_bytes()


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
