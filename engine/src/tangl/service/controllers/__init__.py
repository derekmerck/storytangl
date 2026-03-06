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

__all__ = [
    "get_default_controllers",
]
