from pathlib import Path

import pytest

from tangl.story import World


@pytest.fixture(autouse=True)
def clear_world_instances() -> None:
    clear_instances = getattr(World, "clear_instances", None)
    if callable(clear_instances):
        clear_instances()
    yield
    if callable(clear_instances):
        clear_instances()


@pytest.fixture
def media_mvp_path(resources_dir) -> Path:
    return resources_dir / "worlds" / "media_mvp"
