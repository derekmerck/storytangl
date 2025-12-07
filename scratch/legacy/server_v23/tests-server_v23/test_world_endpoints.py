import pytest
from fastapi.testclient import TestClient
from tangl.rest.app import app
from tangl.config import settings
from tangl.utils.uuid_for_secret import uuid_for_secret

client = TestClient(app, base_url="http://tangl/api/v2/")

world_label = 'reference'

def test_world_info():
    response = client.get(f"world/{world_label}/info")
    assert response.status_code == 200
    update = response.json()
    print( update )
