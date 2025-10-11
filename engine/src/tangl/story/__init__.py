"""Story package shims for legacy imports."""

from __future__ import annotations

import sys
import types
import warnings

from tangl.service.controllers.runtime_controller import RuntimeController

__all__ = ["StoryController"]

_DEPRECATION_MESSAGE = (
    "tangl.story.story_controller is deprecated; import "
    "tangl.service.controllers.RuntimeController instead."
)


def _module_getattr(name: str) -> object:
    if name == "StoryController":
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        return RuntimeController
    raise AttributeError(name)


_deprecated_module = types.ModuleType("tangl.story.story_controller")
_deprecated_module.__all__ = ["StoryController"]
_deprecated_module.__getattr__ = _module_getattr  # type: ignore[attr-defined]

def __getattr__(name: str) -> object:
    if name == "StoryController":
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        return RuntimeController
    raise AttributeError(name)


sys.modules[__name__ + ".story_controller"] = _deprecated_module
