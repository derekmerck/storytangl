"""An anthology's books open by id through the REST app (#610).

Opening the anthology itself used to compile the whole bundle with the default
codec and answer 500; no id named a book, so no client could play one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.rest import media_server
from tangl.rest.app import app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    reset_service_manager_for_testing,
)
from tangl.service import world_registry
from tangl.service.user.user import User
from tangl.story.fabula.world import World
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret

SEARCH_ROOT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "anthology_worlds"
)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [SEARCH_ROOT])
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    reset_service_state_for_testing()
    reset_service_manager_for_testing()
    World.clear_instances()
    secret = settings.client.secret
    user = User(uid=uuid_for_secret(secret))
    user.set_secret(secret)
    get_service_manager().persistence.save(user)

    test_client = TestClient(app, base_url="http://test/api/v2/")
    try:
        yield test_client, {"X-API-Key": key_for_secret(secret)}
    finally:
        test_client.close()
        World.clear_instances()
        reset_service_manager_for_testing()
        reset_service_state_for_testing()


def test_the_world_list_names_each_book_and_its_anthology(
    client: tuple[TestClient, dict[str, str]],
) -> None:
    test_client, _headers = client

    response = test_client.get("system/worlds")

    assert response.status_code == 200
    worlds = {world["label"]: world for world in response.json()}
    assert {label: world.get("anthology") for label, world in worlds.items()} == {
        "shelf_first": "shelf",
        "shelf_second": "shelf",
        "pamphlet": None,
    }
    assert worlds["shelf_first"]["title"] == "The First Book"


def test_a_story_is_created_in_a_book_by_its_id(
    client: tuple[TestClient, dict[str, str]],
) -> None:
    test_client, headers = client

    response = test_client.post(
        "story/create", params={"world_id": "shelf_first"}, headers=headers
    )

    assert response.status_code == 200
    content = " ".join(
        str(fragment.get("content", ""))
        for fragment in response.json()["fragments"]
        if fragment.get("fragment_type") == "content"
    )
    assert "The first book opens." in content


def test_opening_the_anthology_itself_names_its_books(
    client: tuple[TestClient, dict[str, str]],
) -> None:
    test_client, headers = client

    response = test_client.post("story/create", params={"world_id": "shelf"}, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "shelf is an anthology; open one of its books: shelf_first, shelf_second"
    )


def test_a_book_is_preflighted_by_its_id(client: tuple[TestClient, dict[str, str]]) -> None:
    test_client, _headers = client

    response = test_client.get("world/shelf_second/preflight")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_a_book_shows_its_anthologys_media(
    client: tuple[TestClient, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _test_client, headers = client
    monkeypatch.setattr(media_server.app.router, "routes", list(media_server.app.router.routes))

    # Entering the client runs startup, which mounts every world's media.
    with TestClient(app, base_url="http://test/api/v2/") as live:
        response = live.post("story/create", params={"world_id": "shelf_first"}, headers=headers)
        assert response.status_code == 200
        url = next(item["url"] for item in response.json()["fragments"] if item.get("url"))
        asset = live.get(f"http://test{url}")

    assert url == "/media/world/shelf_first/picture.svg"
    assert asset.status_code == 200
    assert asset.content == (SEARCH_ROOT / "shelf" / "media" / "picture.svg").read_bytes()
