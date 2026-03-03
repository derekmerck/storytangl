"""Compatibility barrel for service38 controller classes."""

from __future__ import annotations

from tangl.service38.system_controller import SystemController
from tangl.service38.user.user_controller import UserController
from tangl.story38.fabula.world_controller import WorldController
from tangl.story38.story_controller import RuntimeController


DEFAULT_CONTROLLERS = (
    RuntimeController,
    UserController,
    SystemController,
    WorldController,
)


__all__ = [
    "DEFAULT_CONTROLLERS",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]
