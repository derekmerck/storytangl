"""
.. currentmodule:: tangl.service

Canonical service API for StoryTangl.

The service nucleus is manager-first:

1. :class:`ServiceManager` exposes the explicit public method surface.
2. :func:`service_method` attaches bounded metadata for access, context,
   writeback, blocking behavior, and optional capability tags.
3. Typed response models in :mod:`tangl.service.response` remain the canonical
   payload vocabulary.
4. :class:`RemoteServiceManager` optionally fulfills the same public manager
   contract through the REST API.
"""

from __future__ import annotations

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
from .dispatch import (
    do_advertise_story_info_channels,
    do_advertise_world_info_channels,
    do_get_story_info,
    do_get_world_info,
    service_dispatch,
)
from .response import (
    AuthoringDiagnostic,
    CommandEdgeQuery,
    DirectEdgeRequest,
    EdgeQuery,
    EdgeResolutionRequest,
    FindEdgeRequest,
    FragmentStream,
    InfoModel,
    JsonValue,
    MediaNative,
    NativeResponse,
    PreflightReport,
    RuntimeEnvelope,
    RuntimeEnvelopePayload,
    RuntimeInfo,
    RuntimeMetadata,
    SystemInfo,
    UserInfo,
    UserSecret,
    WorldInfo,
    WorldList,
    WorldSceneList,
    coerce_runtime_info,
)
from .remote_service_manager import RemoteServiceManager
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
from .world_registry import WorldRegistry

__all__ = [
    "AccessDeniedError",
    "AuthMismatchError",
    "AuthoringDiagnostic",
    "BlockingMode",
    "CommandEdgeQuery",
    "DirectEdgeRequest",
    "EdgeQuery",
    "EdgeResolutionRequest",
    "FindEdgeRequest",
    "FragmentStream",
    "InfoModel",
    "InvalidOperationError",
    "JsonValue",
    "MediaNative",
    "NativeResponse",
    "PreflightReport",
    "ResourceNotFoundError",
    "RemoteServiceManager",
    "RuntimeEnvelope",
    "RuntimeEnvelopePayload",
    "RuntimeInfo",
    "RuntimeMetadata",
    "ServiceAccess",
    "ServiceContext",
    "ServiceError",
    "ServiceManager",
    "ServiceMethodSpec",
    "ServiceSession",
    "ServiceWriteback",
    "SystemInfo",
    "UserAuthInfo",
    "UserInfo",
    "UserSecret",
    "ValidationError",
    "WorldInfo",
    "WorldRegistry",
    "build_service_manager",
    "coerce_runtime_info",
    "do_advertise_story_info_channels",
    "do_advertise_world_info_channels",
    "do_get_story_info",
    "do_get_world_info",
    "get_service_method_spec",
    "service_dispatch",
    "service_method",
    "user_id_by_key",
]
