"""
.. currentmodule:: tangl.service

Canonical service API for StoryTangl.

The service nucleus is manager-first:

1. :class:`ServiceManager` exposes the explicit public method surface.
2. :func:`service_method` attaches bounded metadata for access, context,
   writeback, blocking behavior, and optional capability tags.
3. Typed response models in :mod:`tangl.service.response` remain the canonical
   payload vocabulary.

The older orchestrator/gateway/controller stack is still importable as a
compatibility layer, but it is not the canonical public surface anymore.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .auth import UserAuthInfo, user_id_by_key
from .bootstrap import build_service_manager
from .exceptions import (
    AccessDeniedError,
    AuthMismatchError,
    InvalidOperationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from .response import (
    BadgeListValue,
    FragmentStream,
    InfoModel,
    ItemListValue,
    KvListValue,
    MediaNative,
    NativeResponse,
    PrimitiveValue,
    ProjectedItem,
    ProjectedKVItem,
    ProjectedSection,
    ProjectedState,
    RuntimeEnvelope,
    RuntimeInfo,
    ScalarValue,
    SectionValue,
    SystemInfo,
    TableValue,
    UserInfo,
    UserSecret,
    WorldInfo,
    WorldList,
    WorldSceneList,
    coerce_runtime_info,
)
from .service_manager import ServiceManager, ServiceSession
from .service_method import (
    BlockingMode,
    ServiceAccess,
    ServiceContext,
    ServiceMethodSpec,
    ServiceWriteback,
    get_service_method_spec,
    service_method,
)
from .story_info import DefaultStoryInfoProjector, StoryInfoProjector
from .world_registry import WorldRegistry


_COMPAT_EXPORTS: dict[str, tuple[str, str]] = {
    "AccessLevel": (".api_endpoint", "AccessLevel"),
    "ApiEndpoint": (".api_endpoint", "ApiEndpoint"),
    "EndpointPolicy": (".api_endpoint", "EndpointPolicy"),
    "ExecuteOptions": (".orchestrator", "ExecuteOptions"),
    "GatewayExecuteOptions": (".gateway", "GatewayExecuteOptions"),
    "GatewayRequest": (".rest_adapter", "GatewayRequest"),
    "GatewayRestAdapter": (".rest_adapter", "GatewayRestAdapter"),
    "HasApiEndpoints": (".api_endpoint", "HasApiEndpoints"),
    "MethodType": (".api_endpoint", "MethodType"),
    "Orchestrator": (".orchestrator", "Orchestrator"),
    "ResourceBinding": (".api_endpoint", "ResourceBinding"),
    "ResponseType": (".api_endpoint", "ResponseType"),
    "ServiceGateway": (".gateway", "ServiceGateway"),
    "ServiceOperation": (".operations", "ServiceOperation"),
    "WritebackMode": (".api_endpoint", "WritebackMode"),
    "build_service_gateway": (".bootstrap", "build_service_gateway"),
}


def __getattr__(name: str) -> Any:
    """Lazily expose compatibility-layer service symbols."""

    try:
        module_name, attr_name = _COMPAT_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "AccessDeniedError",
    "AuthMismatchError",
    "BadgeListValue",
    "BlockingMode",
    "DefaultStoryInfoProjector",
    "FragmentStream",
    "InfoModel",
    "InvalidOperationError",
    "ItemListValue",
    "KvListValue",
    "MediaNative",
    "NativeResponse",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedKVItem",
    "ProjectedSection",
    "ProjectedState",
    "ResourceNotFoundError",
    "RuntimeEnvelope",
    "RuntimeInfo",
    "ScalarValue",
    "SectionValue",
    "ServiceAccess",
    "ServiceContext",
    "ServiceError",
    "ServiceManager",
    "ServiceMethodSpec",
    "ServiceSession",
    "ServiceWriteback",
    "StoryInfoProjector",
    "SystemInfo",
    "TableValue",
    "UserAuthInfo",
    "UserInfo",
    "UserSecret",
    "ValidationError",
    "WorldInfo",
    "WorldRegistry",
    "build_service_manager",
    "coerce_runtime_info",
    "get_service_method_spec",
    "service_method",
    "user_id_by_key",
]
