import json

import pytest
from fastapi.testclient import TestClient

from tangl.config import settings
from tangl.utils.hash_secret import key_for_secret


def test_openapi_does_not_publish_configured_credentials(client: TestClient) -> None:
    schema = json.dumps(client.app.openapi())

    if settings.client.secret in schema:
        pytest.fail("OpenAPI schema contains the configured client secret")
    if key_for_secret(settings.client.secret) in schema:
        pytest.fail("OpenAPI schema contains the derived client key")


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
    assert update["api_key"] == key_for_secret(settings.client.secret)
    assert update["user_secret"] == settings.client.secret

def test_system_list_worlds(client):
    response = client.get(f"system/worlds")
    assert response.status_code == 200
    update = response.json()
    print( update )
