"""Service orchestrator/gateway surface."""

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
    FragmentStream,
    InfoModel,
    MediaNative,
    NativeResponse,
    RuntimeEnvelope,
    RuntimeInfo,
    SystemInfo,
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
    "EndpointPolicy",
    "ExecuteOptions",
    "FragmentStream",
    "GatewayRequest",
    "GatewayRestAdapter",
    "GatewayExecuteOptions",
    "HasApiEndpoints",
    "InfoModel",
    "InvalidOperationError",
    "MediaNative",
    "MethodType",
    "NativeResponse",
    "Orchestrator",
    "ResourceNotFoundError",
    "RuntimeInfo",
    "RuntimeEnvelope",
    "ResponseType",
    "ResourceBinding",
    "ServiceError",
    "ServiceGateway",
    "ServiceOperation",
    "SystemInfo",
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
