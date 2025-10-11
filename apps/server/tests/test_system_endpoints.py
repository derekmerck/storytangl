
import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.utils.hash_secret import uuid_for_secret


def test_system_get_info(client: TestClient):
    response = client.get(f"system/info")
    print( response.headers, response.url )
    assert response.status_code == 200
    update = response.json()
    print( update )
    assert update['engine'] == 'StoryTangl'

def test_system_get_key(client):
    response = client.get(f"system/secret", params={'secret': settings.client.secret})
    assert response.status_code == 200
    update = response.json()
    print( update )
    assert update['user_secret'] == settings.client.secret
    assert update['user_id'] == str( uuid_for_secret( settings.client.secret) )

def test_system_list_worlds(client, world):
    response = client.get(f"system/worlds")
    assert response.status_code == 200
    update = response.json()
    print( update )
