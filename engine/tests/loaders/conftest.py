from pathlib import Path

import pytest

from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag
from tangl.story import World


@pytest.fixture(autouse=True)
def clear_world_instances() -> None:
    clear_instances = getattr(World, "clear_instances", None)
    if callable(clear_instances):
        clear_instances()
    yield
    if callable(clear_instances):
        clear_instances()


@pytest.fixture(autouse=True)
def clear_media_inventory_cache() -> None:
    clear_cache = getattr(MediaResourceInventoryTag, "clear_from_source_cache", None)
    if callable(clear_cache):
        clear_cache()
    yield
    if callable(clear_cache):
        clear_cache()


@pytest.fixture
def media_mvp_path(resources_dir) -> Path:
    return resources_dir / "worlds" / "media_mvp"
