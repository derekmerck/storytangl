import importlib

import pytest
from fastapi.testclient import TestClient

from tangl.rest.app import app
from tangl.config import settings
from tangl.utils.uuid_for_secret import uuid_for_secret

client = TestClient(app, base_url="http://test/api/v2/")

def test_system_get_info():
    response = client.get(f"system/info")
    print( response.headers, response.url )
    assert response.status_code == 200
    update = response.json()
    print( update )
    assert update['engine'] == 'story-tangl'

def test_system_get_key():
    response = client.get(f"system/secret", params={'secret': settings.client.secret})
    assert response.status_code == 200
    update = response.json()
    print( update )
    assert update['user_secret'] == settings.client.secret
    assert update['user_id'] == str( uuid_for_secret( settings.client.secret) )

def test_system_list_worlds():
    from tangl.story.fabula import World
    World.clear_instances()
    World.load_worlds()

    response = client.get(f"system/worlds")
    assert response.status_code == 200
    update = response.json()
    print( update )
