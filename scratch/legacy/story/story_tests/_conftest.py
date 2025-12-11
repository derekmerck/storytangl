
import pytest

from tangl.story.world import World
from tangl.scripting import ScriptManager


@pytest.fixture
def world(my_script_data):
    World.clear_instances()
    sm = ScriptManager.from_data(my_script_data)
    world = World(label='test_world', script_manager=sm)
    yield world
    World.clear_instances()

