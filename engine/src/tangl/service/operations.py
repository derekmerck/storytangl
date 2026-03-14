"""Operation tokens for service call sites."""

from __future__ import annotations

from enum import Enum


class ServiceOperation(str, Enum):
    """Stable external operation ids mapped to internal controller endpoints.

    The ``STORY38_`` member names and ``"story38."`` string values are a legacy
    version prefix baked into the wire protocol. Renaming the string values
    would break existing API consumers. Member name cleanup (``STORY38_CREATE``
    -> ``STORY_CREATE``) is deferred to a coordinated API versioning pass that
    also updates ``apps/server``, ``apps/cli``, and the test suite.
    """

    STORY38_CREATE = "story38.create"
    STORY38_UPDATE = "story38.update"
    STORY38_DO = "story38.do"
    STORY38_STATUS = "story38.status"
    STORY38_DROP = "story38.drop"

    USER_INFO = "user.info"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DROP = "user.drop"
    USER_KEY = "user.key"

    WORLD_LIST = "world.list"
    WORLD_INFO = "world.info"
    WORLD_MEDIA = "world.media"
    WORLD_LOAD = "world.load"
    WORLD_UNLOAD = "world.unload"

    SYSTEM_INFO = "system.info"
    SYSTEM_RESET = "system.reset"


_OPERATION_ENDPOINTS: dict[ServiceOperation, str] = {
    ServiceOperation.STORY38_CREATE: "RuntimeController.create_story",
    ServiceOperation.STORY38_UPDATE: "RuntimeController.get_story_update",
    ServiceOperation.STORY38_DO: "RuntimeController.resolve_choice",
    ServiceOperation.STORY38_STATUS: "RuntimeController.get_story_info",
    ServiceOperation.STORY38_DROP: "RuntimeController.drop_story",

    ServiceOperation.USER_INFO: "UserController.get_user_info",
    ServiceOperation.USER_CREATE: "UserController.create_user",
    ServiceOperation.USER_UPDATE: "UserController.update_user",
    ServiceOperation.USER_DROP: "UserController.drop_user",
    ServiceOperation.USER_KEY: "UserController.get_key_for_secret",

    ServiceOperation.WORLD_LIST: "WorldController.list_worlds",
    ServiceOperation.WORLD_INFO: "WorldController.get_world_info",
    ServiceOperation.WORLD_MEDIA: "WorldController.get_world_media",
    ServiceOperation.WORLD_LOAD: "WorldController.load_world",
    ServiceOperation.WORLD_UNLOAD: "WorldController.unload_world",

    ServiceOperation.SYSTEM_INFO: "SystemController.get_system_info",
    ServiceOperation.SYSTEM_RESET: "SystemController.reset_system",
}


_ENDPOINT_OPERATION = {endpoint: op for op, endpoint in _OPERATION_ENDPOINTS.items()}


def endpoint_for_operation(operation: ServiceOperation | str) -> str:
    """Resolve a service operation token to controller endpoint name."""

    op = operation if isinstance(operation, ServiceOperation) else ServiceOperation(operation)
    return _OPERATION_ENDPOINTS[op]


def operation_for_endpoint(endpoint_name: str) -> ServiceOperation:
    """Resolve a controller endpoint name back to a service operation token."""

    try:
        return _ENDPOINT_OPERATION[endpoint_name]
    except KeyError as exc:
        raise KeyError(f"No service operation token for endpoint '{endpoint_name}'") from exc

__all__ = [
    "ServiceOperation",
    "endpoint_for_operation",
    "operation_for_endpoint",
]
