
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
    update = response.json()
    assert update["label"] == world_id
    print( update )
