"""Fresh-process JSON auth and story recovery using the real REST lifespan."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient

from tangl.config import settings


def main(phase: str, root: Path) -> None:
    settings.set("service.paths.worlds", [root / "worlds"])
    for key in ("user_data", "story_media", "cache_data"):
        settings.set(f"service.paths.{key}", root / key)
    settings.set("service.persistence", "json_file")
    settings.set("client.secret", "json-auth-bootstrap")

    from tangl.rest.app import app
    from tangl.story import World

    secret = "json-auth-player"
    receipt = root / "receipt.json"
    if phase == "seed":
        with TestClient(app) as client:
            response = client.post("/api/v2/user/create", params={"secret": secret})
            assert response.status_code == 200
            credentials = response.json()
            headers = {"X-API-Key": credentials["api_key"]}
            created = client.post(
                "/api/v2/story/create", params={"world_id": "reference"}, headers=headers,
            )
            assert created.status_code == 200
            envelope = created.json()
            for text in ("Approach the fireplace", "I'm looking for the Northern Pass"):
                choice = next(item for item in envelope["fragments"] if item.get("text") == text)
                moved = client.post(
                    "/api/v2/story/do", json={"edge_id": choice["edge_id"]}, headers=headers,
                )
                assert moved.status_code == 200
                envelope = moved.json()
            assert envelope["step"] == 3
            user = client.get("/api/v2/user/info", headers=headers)
            assert user.status_code == 200
            assert user.json()["current_ledger_id"] == created.json()["metadata"]["ledger_id"]
            receipt.write_text(json.dumps({
                "user": user.json(), "current": envelope,
            }), encoding="utf-8")
        return

    assert World.get_instance("reference") is None
    expected = json.loads(receipt.read_text(encoding="utf-8"))
    with TestClient(app) as client:
        assert World.get_instance("reference") is None
        credentials = client.get("/api/v2/system/secret", params={"secret": secret})
        assert credentials.status_code == 200
        headers = {"X-API-Key": credentials.json()["api_key"]}
        user = client.get("/api/v2/user/info", headers=headers)
        assert user.status_code == 200
        assert user.json()["user_id"] == expected["user"]["user_id"]
        assert user.json()["current_ledger_id"] == expected["user"]["current_ledger_id"]
        unknown = client.get("/api/v2/system/secret", params={"secret": "unknown"}).json()
        denied = client.get(
            "/api/v2/user/info", headers={"X-API-Key": unknown["api_key"]},
        )
        assert denied.status_code == 401
        assert client.post("/api/v2/user/create").status_code == 200
        # Only the first story request resolves the World; nothing above warms it.
        assert World.get_instance("reference") is None
        response = client.get("/api/v2/story/update", headers=headers)
        assert response.status_code == 200
        restored = response.json()
        before = expected["current"]
        for key in ("cursor_id", "step"):
            assert restored[key] == before[key]
        assert restored["metadata"]["ledger_id"] == before["metadata"]["ledger_id"]
        assert restored["metadata"]["world_id"] == "reference"
        assert any(
            "The Crossroads Inn sits" in str(item.get("content", ""))
            for item in restored["fragments"]
        )
        current_response = client.get(
            "/api/v2/story/update", params={"since_step": restored["step"]}, headers=headers,
        )
        assert current_response.status_code == 200
        current = current_response.json()

        def choices(envelope: dict) -> list[dict]:
            return [
                {key: item[key] for key in ("uid", "edge_id", "text")}
                for item in envelope["fragments"] if item["fragment_type"] == "choice"
            ]
        assert choices(current) == choices(before)
        historical_media = next(
            item for item in restored["fragments"] if item.get("url", "").endswith("tavern.svg")
        )
        image = client.get(historical_media["url"])
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/svg+xml"
        assert image.content == (root / "worlds/reference/media/images/tavern.svg").read_bytes()
        next_choice = next(
            item for item in current["fragments"]
            if item.get("text") == "Offer to split any treasure found"
        )
        moved = client.post(
            "/api/v2/story/do", json={"edge_id": next_choice["edge_id"]}, headers=headers,
        )
        assert moved.status_code == 200
        after = moved.json()
        assert after["metadata"]["ledger_id"] == before["metadata"]["ledger_id"]
        assert after["step"] > current["step"]
        assert after["cursor_id"] != current["cursor_id"]
        readback_response = client.get(
            "/api/v2/story/update", params={"since_step": after["step"]}, headers=headers,
        )
        assert readback_response.status_code == 200
        readback = readback_response.json()
        assert readback["metadata"]["ledger_id"] == after["metadata"]["ledger_id"]
        assert readback["step"] == after["step"]
        assert readback["cursor_id"] == after["cursor_id"]
        assert choices(readback) == choices(after)


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
