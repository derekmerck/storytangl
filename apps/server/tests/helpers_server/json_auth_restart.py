"""Fresh-process JSON authentication witness using the real REST lifespan."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

from tangl.config import settings


def main(phase: str, root: Path) -> None:
    settings.set("service.paths.worlds", [root / "worlds"])
    for key in ("user_data", "story_media", "cache_data"):
        settings.set(f"service.paths.{key}", root / key)
    settings.set("service.persistence", "json_file")
    settings.set("service.caches.shelved", False)
    settings.set("client.secret", "json-auth-bootstrap")

    from tangl.core import Graph
    from tangl.rest.app import app
    from tangl.story import World
    from tangl.vm import Ledger

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
            user = client.get("/api/v2/user/info", headers=headers)
            assert user.status_code == 200
            assert user.json()["current_ledger_id"] == created.json()["metadata"]["ledger_id"]
            receipt.write_text(json.dumps(user.json()), encoding="utf-8")
        return

    assert World.get_instance("reference") is None
    expected = json.loads(receipt.read_text(encoding="utf-8"))
    # No auth path, including lifespan's create/restore user, may hydrate a ledger.
    with (
        patch.object(Ledger, "structure", side_effect=AssertionError("Auth restored Ledger")),
        patch.object(Graph, "structure", side_effect=AssertionError("Auth restored Graph")),
    ):
        with TestClient(app) as client:
            assert World.get_instance("reference") is None
            credentials = client.get("/api/v2/system/secret", params={"secret": secret})
            assert credentials.status_code == 200
            headers = {"X-API-Key": credentials.json()["api_key"]}
            user = client.get("/api/v2/user/info", headers=headers)
            assert user.status_code == 200
            assert user.json()["user_id"] == expected["user_id"]
            assert user.json()["current_ledger_id"] == expected["current_ledger_id"]
            unknown = client.get("/api/v2/system/secret", params={"secret": "unknown"}).json()
            denied = client.get(
                "/api/v2/user/info", headers={"X-API-Key": unknown["api_key"]},
            )
            assert denied.status_code == 401
            assert client.post("/api/v2/user/create").status_code == 200
            assert World.get_instance("reference") is None


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
