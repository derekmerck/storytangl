from fastapi.testclient import TestClient
import pytest

from tangl.rest.app import app

# from tests.conftest import my_script_data
# from tests.story.conftest import world

@pytest.fixture(scope="session")
def world():
    from tangl.ir.core_ir import ScriptMetadata
    from tangl.ir.story_ir import StoryScript
    from tangl.story.fabula.world import World, ScriptManager
    master_script = StoryScript(
        label="test_world",
        metadata=ScriptMetadata(title="Hello World!", author="TanglDev"),
        scenes=[]
    )
    script_manager = ScriptManager(master_script=master_script)
    return World(label="test_world", script_manager=script_manager)

@pytest.fixture
def client():
    return TestClient(app, base_url="http://test/api/v2/")
