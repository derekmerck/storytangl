"""Operation tokens for service call sites."""

from __future__ import annotations

from enum import Enum


class ServiceOperation(str, Enum):
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

# Temporary compatibility during endpoint-name retirement.
_ENDPOINT_ALIASES: dict[str, str] = {
    "RuntimeController.create_story38": "RuntimeController.create_story",
    "RuntimeController.get_story_update38": "RuntimeController.get_story_update",
    "RuntimeController.resolve_choice38": "RuntimeController.resolve_choice",
    "RuntimeController.get_story_info38": "RuntimeController.get_story_info",
    "RuntimeController.drop_story38": "RuntimeController.drop_story",
}


def endpoint_for_operation(operation: ServiceOperation | str) -> str:
    """Resolve a service operation token to controller endpoint name."""

    op = operation if isinstance(operation, ServiceOperation) else ServiceOperation(operation)
    return _OPERATION_ENDPOINTS[op]


def operation_for_endpoint(endpoint_name: str) -> ServiceOperation:
    """Resolve a controller endpoint name back to a service operation token."""

    canonical_endpoint = _ENDPOINT_ALIASES.get(endpoint_name, endpoint_name)
    try:
        return _ENDPOINT_OPERATION[canonical_endpoint]
    except KeyError as exc:
        raise KeyError(f"No service operation token for endpoint '{endpoint_name}'") from exc


# Backwards-compatible alias retained during naming cutover.
ServiceOperation38 = ServiceOperation


__all__ = [
    "ServiceOperation",
    "ServiceOperation38",
    "endpoint_for_operation",
    "operation_for_endpoint",
]
