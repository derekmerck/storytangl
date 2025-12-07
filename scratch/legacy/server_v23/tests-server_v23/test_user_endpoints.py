import pytest
from fastapi.testclient import TestClient
from tangl.rest.app import app
from tangl.config import settings
from tangl.utils.uuid_for_secret import uuid_for_secret

client = TestClient(app, base_url="http://tangl/api/v2/")

def test_system_create_user():
    response = client.post(f"user/create", params={'secret': settings.client.secret})
    assert response.status_code == 200
    update = response.json()
    print( update )

    assert update[0] == str( uuid_for_secret(settings.client.secret) )
    assert update[1] == settings.client.secret
