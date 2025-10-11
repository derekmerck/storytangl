from typing import TYPE_CHECKING

from .api_endpoint import ApiEndpoint, MethodType, AccessLevel, ResponseType, HasApiEndpoints
from .controllers import ApiKeyInfo, RuntimeController, UserController
from .orchestrator import Orchestrator
from .service_manager import ServiceManager

__all__ = [
    "AccessLevel",
    "ApiEndpoint",
    "ApiKeyInfo",
    "HasApiEndpoints",
    "MethodType",
    "Orchestrator",
    "ResponseType",
    "RuntimeController",
    "ServiceManager",
    "SystemController",
    "UserController",
    "WorldController",
]

if TYPE_CHECKING:  # pragma: no cover - type checkers can resolve eagerly
    from .controllers.system_controller import SystemController
    from .controllers.world_controller import WorldController


def __getattr__(name: str):  # pragma: no cover - defer heavy imports
    if name == "SystemController":
        from .controllers.system_controller import SystemController as _SystemController

        return _SystemController
    if name == "WorldController":
        from .controllers.world_controller import WorldController as _WorldController

        return _WorldController
    raise AttributeError(name)
