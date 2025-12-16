from pathlib import Path

import pytest

from tangl.story.fabula import World

@pytest.fixture(autouse=True)
def clear_world():
    World.clear_instances()
    yield
    World.clear_instances()

@pytest.fixture
def media_mvp_path(resources_dir) -> Path:
    return resources_dir / "worlds" / "media_mvp"
