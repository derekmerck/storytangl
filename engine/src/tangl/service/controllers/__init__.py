from __future__ import annotations

"""Service-layer controller exports."""

from typing import TYPE_CHECKING

from .runtime_controller import RuntimeController
from .user_controller import ApiKeyInfo, UserController

__all__ = [
    "ApiKeyInfo",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .system_controller import SystemController
    from .world_controller import WorldController


def __getattr__(name: str):  # pragma: no cover - simple lazy import helper
    if name == "SystemController":
        from .system_controller import SystemController as _SystemController

        return _SystemController
    if name == "WorldController":
        from .world_controller import WorldController as _WorldController

        return _WorldController
    raise AttributeError(name)
