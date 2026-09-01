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
    """Guarantee the repartee world's phrase singletons are registered.

    ``PhraseType`` definitions register when the world's domain module is
    imported. A full-suite run can clear those registries after the module is
    already in ``sys.modules``, so a later compile finds no definitions and
    badge construction fails validation. Reload only when they are actually
    missing — an unconditional reload rebinds classes that live instances
    still reference.
    """

    import importlib
    import sys

    from tangl.mechanics.games import PhraseType

    if PhraseType.get_instance("repartee_starter_call") is None:
        module = sys.modules.get("repartee_loop.domain")
        if module is not None:
            importlib.reload(module)
    return "repartee_loop"
