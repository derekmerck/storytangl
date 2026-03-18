"""
.. currentmodule:: tangl.service

Service orchestration surface between applications and the narrative engine.

Conceptual layers
-----------------

1. Gateway and transport adaptation

   - :class:`ServiceGateway` executes tokenized :class:`ServiceOperation`
     requests with inbound/outbound hooks and render profiles.
   - :class:`GatewayRestAdapter` normalizes transport calls (auth resolution,
     request envelopes) onto the gateway.
   - :func:`build_service_gateway` wires a configured gateway from a
     persistence manager.

2. Orchestration

   - :class:`Orchestrator` maps endpoint names to controller methods,
     hydrates ``User``, ``Ledger``, and ``Frame`` dependencies from type
     hints, and manages persistence writeback.
   - :class:`ApiEndpoint` decorates controller methods with access level,
     method type, response type, and resource binding metadata.

3. Controllers

   - :class:`~controllers.RuntimeController` — story session lifecycle
     (create, advance, query, drop).
   - :class:`~controllers.WorldController` — world catalog and loading.
   - :class:`~controllers.UserController` — user CRUD and authentication.
   - :class:`~controllers.SystemController` — health and diagnostics.

4. Response and auth primitives

   - :class:`RuntimeInfo`, :class:`RuntimeEnvelope`, :class:`InfoModel`,
     and domain info models define the native response vocabulary.
   - :class:`UserAuthInfo` and :func:`user_id_by_key` handle API key
     resolution.
   - :class:`ServiceError` and subclasses map domain errors to response
     codes.

Design intent
-------------
``tangl.service`` is the **only** interface between applications and the engine.
Transport layers (CLI, REST, future GraphQL) call the gateway or orchestrator;
controllers contain domain logic; the engine layers below (core, vm, story)
never import from service.
"""

from .api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    EndpointPolicy,
    HasApiEndpoints,
    MethodType,
    ResourceBinding,
    ResponseType,
    WritebackMode,
)
from .auth import UserAuthInfo, user_id_by_key
from .bootstrap import build_service_gateway
from .exceptions import (
    AccessDeniedError,
    AuthMismatchError,
    InvalidOperationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from .gateway import GatewayExecuteOptions, ServiceGateway
from .operations import ServiceOperation
from .orchestrator import ExecuteOptions, Orchestrator
from .rest_adapter import GatewayRequest, GatewayRestAdapter
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
from .world_registry import WorldRegistry


__all__ = [
    "AccessDeniedError",
    "AccessLevel",
    "ApiEndpoint",
    "AuthMismatchError",
    "BadgeListValue",
    "EndpointPolicy",
    "ExecuteOptions",
    "FragmentStream",
    "GatewayRequest",
    "GatewayRestAdapter",
    "GatewayExecuteOptions",
    "HasApiEndpoints",
    "InfoModel",
    "InvalidOperationError",
    "ItemListValue",
    "KvListValue",
    "MediaNative",
    "MethodType",
    "NativeResponse",
    "Orchestrator",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedKVItem",
    "ProjectedSection",
    "ProjectedState",
    "ResourceNotFoundError",
    "RuntimeInfo",
    "RuntimeEnvelope",
    "ResponseType",
    "ResourceBinding",
    "ScalarValue",
    "SectionValue",
    "ServiceError",
    "ServiceGateway",
    "ServiceOperation",
    "SystemInfo",
    "TableValue",
    "UserAuthInfo",
    "UserInfo",
    "UserSecret",
    "ValidationError",
    "WorldInfo",
    "WorldList",
    "WorldRegistry",
    "WorldSceneList",
    "WritebackMode",
    "build_service_gateway",
    "coerce_runtime_info",
    "user_id_by_key",
]
