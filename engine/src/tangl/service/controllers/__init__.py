"""Controller package exports.

Concrete controller modules are imported lazily so lower-layer modules can use
service support types without eagerly pulling the full controller stack into
package initialization.
"""

from __future__ import annotations


def get_default_controllers() -> tuple[type, ...]:
    """Return the standard controller set with lazy imports."""
    from .runtime_controller import RuntimeController
    from .system_controller import SystemController
    from .user_controller import UserController
    from .world_controller import WorldController

    return (
        RuntimeController,
        UserController,
        SystemController,
        WorldController,
    )


def __getattr__(name: str):
    """Lazily expose controller classes for compatibility imports."""
    if name == "RuntimeController":
        from .runtime_controller import RuntimeController

        return RuntimeController
    if name == "SystemController":
        from .system_controller import SystemController

        return SystemController
    if name == "UserController":
        from .user_controller import UserController

        return UserController
    if name == "ApiKeyInfo":
        from .user_controller import ApiKeyInfo

        return ApiKeyInfo
    if name == "WorldController":
        from .world_controller import WorldController

        return WorldController
    raise AttributeError(name)


__all__ = [
    "ApiKeyInfo",
    "get_default_controllers",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]
