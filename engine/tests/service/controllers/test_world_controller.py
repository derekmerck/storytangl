"""WorldController lifecycle contract tests."""

from __future__ import annotations

import pytest

from tangl.service.controllers.world_controller import WorldController, _MANUAL_WORLDS
from tangl.story import World


@pytest.fixture(autouse=True)
def clear_manual_worlds() -> None:
    _MANUAL_WORLDS.clear()
    World.clear_instances()
    yield
    _MANUAL_WORLDS.clear()
    World.clear_instances()


def _script_data() -> dict[str, object]:
    return {
        "label": "script_label",
        "metadata": {
            "title": "The Crossroads",
            "author": "Tests",
        },
        "scenes": {},
    }


def test_load_world_uses_legacy_label_during_singleton_construction() -> None:
    controller = WorldController()

    result = controller.load_world(script_data=_script_data())

    world = _MANUAL_WORLDS["the_crossroads"]
    assert isinstance(world, World)
    assert world.label == "the_crossroads"
    assert World.get_instance("the_crossroads") is world
    assert World.get_instance("script_label") is None
    assert result.details["world_label"] == "the_crossroads"
