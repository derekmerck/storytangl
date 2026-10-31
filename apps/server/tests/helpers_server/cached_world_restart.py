"""Run one fresh-process phase of the cache-enabled REST witness."""
from __future__ import annotations

import json
import shelve
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from tangl.config import settings


def main(phase: str, root: Path) -> None:
    settings.set("service.paths.worlds", [root / "worlds"])
    for name in ("user_data", "story_media", "cache_data"):
        settings.set(f"service.paths.{name}", root / name)
    settings.set("service.persistence", "json_file")
    settings.set("client.secret", "isolation-bootstrap")

    from tangl.rest.app import app
    from tangl.media import MediaResourceInventoryTag
    from tangl.service.response import RuntimeEnvelopePayload
    from tangl.story import World
    from tangl.utils import shelved2

    labels = ("isolation_alpha", "isolation_beta")
    assert shelved2.SHELVED_CACHE_ENABLED
    assert shelved2.cache_dir == root / "cache_data"
    receipt = root / "world-receipt.json"

    def response_json(response):
        assert response.status_code == 200, (response.status_code, response.text)
        return response.json()

    def envelope(response):
        data = response_json(response)
        RuntimeEnvelopePayload.model_validate(data)
        return data

    def choice(frame, text):
        return next(item for item in frame["fragments"]
                    if item.get("fragment_type") == "choice" and item.get("text") == text)

    def inspect(client, headers, label, marker):
        info = response_json(client.get("/api/v2/story/info", params={"channels": "ui-mystery"},
                                        headers=headers))
        section = next(item for item in info["sections"] if item["section_id"] == "world_state")
        values = {row["key"]: row["value"] for row in section["value"]["items"]}
        assert values == {
            "catalog_key": label, "marker": marker, "namespace_marker": marker,
        }, values
        image = client.get(f"/media/world/{label}/picture.svg")
        assert image.status_code == 200
        assert image.content == (root / "worlds" / label / "media/picture.svg").read_bytes()

    with TestClient(app) as client:
        assert all(World.get_instance(label) is None for label in labels)
        listed = response_json(client.get("/api/v2/system/worlds"))
        assert {item["label"] for item in listed} >= {*labels, "shelf_first", "shelf_second"}
        assert all(World.get_instance(label) is None for label in labels)
        if phase == "seed":
            stories = {}
            for label in labels:
                secret = f"{label}-user"
                credentials = response_json(
                    client.post("/api/v2/user/create", params={"secret": secret})
                )
                headers = {"X-API-Key": credentials["api_key"]}
                frame = envelope(client.post("/api/v2/story/create", params={"world_id": label},
                                             headers=headers))
                assert frame["metadata"]["world_id"] == label
                assert f"{label} start" in json.dumps(frame)
                inspect(client, headers, label, "none")
                stories[label] = {"secret": secret, "user_id": credentials["user_id"],
                                  "initial": frame, "headers": headers}
            assert stories[labels[0]]["user_id"] != stories[labels[1]]["user_id"]
            alpha, beta = (stories[label]["initial"] for label in labels)
            assert alpha["metadata"]["ledger_id"] != beta["metadata"]["ledger_id"]
            assert alpha["cursor_id"] != beta["cursor_id"]
            assert choice(alpha, "Continue")["edge_id"] != choice(beta, "Continue")["edge_id"]
            assert next(f["rit_id"] for f in alpha["fragments"] if f.get("url")) != next(
                f["rit_id"] for f in beta["fragments"] if f.get("url")
            )
            for label in (labels[0], labels[1], labels[0]):
                item = stories[label]
                current = envelope(client.get("/api/v2/story/update", headers=item["headers"]))
                if "middle" not in item:
                    moved = envelope(client.post("/api/v2/story/do", headers=item["headers"],
                        json={"edge_id": choice(current, "Continue")["edge_id"]}))
                    assert f"{label} middle" in json.dumps(moved)
                    assert moved["cursor_id"] != current["cursor_id"]
                    item["middle"] = moved
                else:
                    assert current["cursor_id"] == item["middle"]["cursor_id"]
                inspect(client, item["headers"], label, label)
            assert shelved2.miss_count >= 2
            assert list((root / "cache_data").glob("rits-v2*"))
            with shelve.open(str(root / "cache_data/rits-v2"), flag="r") as cached_media:
                for label in labels:
                    path = root / "worlds" / label / "media/picture.svg"
                    key = shelved2.generate_key(MediaResourceInventoryTag, path)
                    assert cached_media[key][0].path == path
            for book in ("shelf_first", "shelf_second"):
                credential = response_json(
                    client.post("/api/v2/user/create", params={"secret": book})
                )
                book_headers = {"X-API-Key": credential["api_key"]}
                frame = envelope(client.post("/api/v2/story/create", params={"world_id": book},
                                             headers=book_headers))
                assert frame["metadata"]["world_id"] == book
                assert ("The first book opens." if book.endswith("first") else
                        "The second book opens.") in json.dumps(frame)
                asset = client.get(f"/media/world/{book}/picture.svg")
                assert asset.status_code == 200
                assert asset.content == (root / "worlds/shelf/media/picture.svg").read_bytes()
            receipt.write_text(json.dumps(stories))
            return

        stories = json.loads(receipt.read_text())
        headers_by_world = {}
        completed = {}
        for label in labels:
            item = stories[label]
            credentials = response_json(client.get("/api/v2/system/secret",
                                                   params={"secret": item["secret"]}))
            headers = {"X-API-Key": credentials["api_key"]}
            user = response_json(client.get("/api/v2/user/info", headers=headers))
            assert user["user_id"] == item["user_id"]
            assert user["current_ledger_id"] == item["middle"]["metadata"]["ledger_id"]
            headers_by_world[label] = headers
        assert all(World.get_instance(label) is None for label in labels)
        for index, label in enumerate((labels[0], labels[1], labels[0])):
            item, headers = stories[label], headers_by_world[label]
            restored = envelope(client.get("/api/v2/story/update", headers=headers))
            assert World.get_instance(label) is not None
            if index == 0:
                assert World.get_instance(labels[1]) is None
            before = item["middle"]
            assert restored["metadata"]["world_id"] == label
            assert restored["metadata"]["ledger_id"] == before["metadata"]["ledger_id"]
            assert restored["cursor_id"] == before["cursor_id"]
            assert restored["step"] == before["step"]
            original_media = next(f for f in item["initial"]["fragments"] if f.get("url"))
            restored_media = next(f for f in restored["fragments"] if f.get("url"))
            for field in ("uid", "source_id", "rit_id", "url"):
                assert restored_media[field] == original_media[field]
            current = envelope(client.get("/api/v2/story/update", headers=headers,
                                          params={"since_step": restored["step"]}))
            assert choice(current, "Finish")["edge_id"] == choice(before, "Finish")["edge_id"]
            inspect(client, headers, label, label)
        assert shelved2.hit_count >= 2
        for label in labels:
            headers = headers_by_world[label]
            current = envelope(client.get("/api/v2/story/update", headers=headers))
            moved = envelope(client.post("/api/v2/story/do", headers=headers,
                                        json={"edge_id": choice(current, "Finish")["edge_id"]}))
            assert f"{label} end" in json.dumps(moved)
            assert moved["step"] > current["step"] and moved["cursor_id"] != current["cursor_id"]
            inspect(client, headers, label, label)
            completed[label] = moved
        reread = envelope(client.get("/api/v2/story/update", headers=headers_by_world[labels[0]]))
        assert reread["cursor_id"] == completed[labels[0]]["cursor_id"]
        assert reread["step"] == completed[labels[0]]["step"]
        inspect(client, headers_by_world[labels[0]], labels[0], labels[0])


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
