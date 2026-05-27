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
    do_advertise_info_channels,
    do_get_story_info,
    on_advertise_info_channels,
    on_get_story_info,
)
from .response import (
    AuthoringDiagnostic,
    BadgeListValue,
    FragmentStream,
    InfoAffordance,
    InfoModel,
    InfoState,
    ItemListValue,
    JsonValue,
    KvRow,
    KvListValue,
    MediaNative,
    NativeResponse,
    PreflightReport,
    PrimitiveValue,
    ProjectedItem,
    ProjectedSection,
    ProjectedState,
    RuntimeEnvelope,
    RuntimeInfo,
    ScalarValue,
    SectionValue,
    StoryInfoRequest,
    SystemInfo,
    TableValue,
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
from .story_info import DefaultStoryInfoProjector, StoryInfoProjector
from .world_registry import WorldRegistry

__all__ = [
    "AccessDeniedError",
    "AuthMismatchError",
    "AuthoringDiagnostic",
    "BadgeListValue",
    "BlockingMode",
    "DefaultStoryInfoProjector",
    "FragmentStream",
    "InfoAffordance",
    "InfoModel",
    "InfoState",
    "InvalidOperationError",
    "ItemListValue",
    "JsonValue",
    "KvListValue",
    "KvRow",
    "MediaNative",
    "NativeResponse",
    "PreflightReport",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedSection",
    "ProjectedState",
    "ResourceNotFoundError",
    "RemoteServiceManager",
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
    "StoryInfoRequest",
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
    "do_advertise_info_channels",
    "do_get_story_info",
    "get_service_method_spec",
    "on_advertise_info_channels",
    "on_get_story_info",
    "service_method",
    "user_id_by_key",
]
