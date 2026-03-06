"""Compatibility barrel for service38 controller classes."""

from __future__ import annotations

from .runtime_controller import RuntimeController
from .system_controller import SystemController
from .user_controller import ApiKeyInfo, UserController
from .world_controller import WorldController

DEFAULT_CONTROLLERS = (
    RuntimeController,
    UserController,
    SystemController,
    WorldController,
)

__all__ = [
    "ApiKeyInfo",
    "DEFAULT_CONTROLLERS",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]
