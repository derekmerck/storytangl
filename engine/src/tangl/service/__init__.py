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
from .response import (
    AuthoringDiagnostic,
    BadgeListValue,
    FragmentStream,
    InfoModel,
    ItemListValue,
    KvListValue,
    MediaNative,
    NativeResponse,
    PreflightReport,
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
    "InfoModel",
    "InvalidOperationError",
    "ItemListValue",
    "KvListValue",
    "MediaNative",
    "NativeResponse",
    "PreflightReport",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedKVItem",
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
