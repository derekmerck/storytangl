from fastapi.testclient import TestClient
import pytest

from tangl.rest.app import app

# from tests.conftest import my_script_data
# from tests.story.conftest import world

@pytest.fixture
def client():
    return TestClient(app, base_url="http://test/api/v2/")

