"""Test isolation for the pygame adapter.

Engine tests get world/registry isolation from ``engine/tests/conftest.py``;
app tests live outside that tree and need their own.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_story_world_instances() -> Iterator[None]:
    """Keep story world singletons isolated between tests."""

    from tangl.service.world_registry import clear_discovered_world_registries
    from tangl.story import World

    clear_discovered_world_registries()
    World.clear_instances()
    yield
    World.clear_instances()
    clear_discovered_world_registries()


@pytest.fixture
def repartee_world() -> str:
    """Return the repartee-loop world key."""
    return "repartee_loop"
