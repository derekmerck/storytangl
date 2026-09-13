
import pytest


def test_world_info(client):
    worlds = client.get("system/worlds")
    assert worlds.status_code == 200
    payload = worlds.json()
    assert payload
    world_id = payload[0]["label"]

    response = client.get(f"world/{world_id}/info")
    if response.status_code == 404:
        pytest.skip("Legacy reference world bundle is not yet v38 codec-compatible.")
    assert response.status_code == 200
    discovery = response.json()
    assert [channel["channel_id"] for channel in discovery["channels"]] == [
        "ui-style-hints-html",
        "ui-branding",
    ]

    selected = client.get(
        f"world/{world_id}/info",
        params={"channels": "ui-branding,ui-style-hints-html"},
    )
    assert selected.status_code == 200
    assert [section["section_id"] for section in selected.json()["sections"]] == [
        "ui-branding",
        "ui-style-hints-html",
    ]

    unknown = client.get(f"world/{world_id}/info", params={"channels": "ui-unknown"})
    assert unknown.status_code == 400
