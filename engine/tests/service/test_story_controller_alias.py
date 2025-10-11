from __future__ import annotations

import importlib
import sys

import pytest


def _reload_story_package() -> None:
    sys.modules.pop("tangl.story.story_controller", None)
    story_pkg = importlib.import_module("tangl.story")
    importlib.reload(story_pkg)


def test_story_controller_module_alias_warns_and_maps_to_runtime() -> None:
    _reload_story_package()
    module = importlib.import_module("tangl.story.story_controller")
    from tangl.service.controllers.runtime_controller import RuntimeController

    with pytest.warns(DeprecationWarning):
        alias = module.StoryController

    assert alias is RuntimeController


def test_story_package_attribute_alias_warns() -> None:
    _reload_story_package()
    story_pkg = importlib.import_module("tangl.story")
    from tangl.service.controllers.runtime_controller import RuntimeController

    with pytest.warns(DeprecationWarning):
        alias = story_pkg.StoryController

    assert alias is RuntimeController
