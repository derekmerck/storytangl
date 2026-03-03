"""Operation tokens for service38 call sites."""

from __future__ import annotations

from enum import Enum


class ServiceOperation38(str, Enum):
    """Stable external operation ids mapped to internal controller endpoints."""

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


_OPERATION_ENDPOINTS: dict[ServiceOperation38, str] = {
    ServiceOperation38.STORY38_CREATE: "RuntimeController.create_story38",
    ServiceOperation38.STORY38_UPDATE: "RuntimeController.get_story_update38",
    ServiceOperation38.STORY38_DO: "RuntimeController.resolve_choice38",
    ServiceOperation38.STORY38_STATUS: "RuntimeController.get_story_info38",
    ServiceOperation38.STORY38_DROP: "RuntimeController.drop_story38",

    ServiceOperation38.USER_INFO: "UserController.get_user_info",
    ServiceOperation38.USER_CREATE: "UserController.create_user",
    ServiceOperation38.USER_UPDATE: "UserController.update_user",
    ServiceOperation38.USER_DROP: "UserController.drop_user",
    ServiceOperation38.USER_KEY: "UserController.get_key_for_secret",

    ServiceOperation38.WORLD_LIST: "WorldController.list_worlds",
    ServiceOperation38.WORLD_INFO: "WorldController.get_world_info",
    ServiceOperation38.WORLD_MEDIA: "WorldController.get_world_media",
    ServiceOperation38.WORLD_LOAD: "WorldController.load_world",
    ServiceOperation38.WORLD_UNLOAD: "WorldController.unload_world",

    ServiceOperation38.SYSTEM_INFO: "SystemController.get_system_info",
    ServiceOperation38.SYSTEM_RESET: "SystemController.reset_system",
}


_ENDPOINT_OPERATION = {endpoint: op for op, endpoint in _OPERATION_ENDPOINTS.items()}


def endpoint_for_operation(operation: ServiceOperation38 | str) -> str:
    """Resolve a service38 operation token to controller endpoint name."""

    op = operation if isinstance(operation, ServiceOperation38) else ServiceOperation38(operation)
    return _OPERATION_ENDPOINTS[op]


def operation_for_endpoint(endpoint_name: str) -> ServiceOperation38:
    """Resolve a controller endpoint name back to a service38 operation token."""

    try:
        return _ENDPOINT_OPERATION[endpoint_name]
    except KeyError as exc:
        raise KeyError(f"No service38 operation token for endpoint '{endpoint_name}'") from exc


__all__ = [
    "ServiceOperation38",
    "endpoint_for_operation",
    "operation_for_endpoint",
]
