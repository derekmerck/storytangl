"""Service orchestrator/gateway surface."""

from .api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    ApiEndpoint38,
    EndpointPolicy,
    HasApiEndpoints,
    MethodType,
    ResourceBinding,
    ResponseType,
    WritebackMode,
)
from .auth import UserAuthInfo, user_id_by_key
from .bootstrap import build_service_gateway, build_service_gateway38
from .exceptions import (
    AccessDeniedError,
    AuthMismatchError,
    InvalidOperationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from .gateway import GatewayExecuteOptions, ServiceGateway, ServiceGateway38
from .operations import ServiceOperation, ServiceOperation38
from .orchestrator import ExecuteOptions, Orchestrator, Orchestrator38
from .rest_adapter import (
    GatewayRequest,
    GatewayRequest38,
    GatewayRestAdapter,
    GatewayRestAdapter38,
)
from .response import (
    FragmentStream,
    InfoModel,
    MediaNative,
    NativeResponse,
    RuntimeEnvelope,
    RuntimeEnvelope38,
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
    "ApiEndpoint38",
    "AuthMismatchError",
    "EndpointPolicy",
    "ExecuteOptions",
    "FragmentStream",
    "GatewayRequest",
    "GatewayRestAdapter",
    "GatewayExecuteOptions",
    "GatewayRequest38",
    "GatewayRestAdapter38",
    "HasApiEndpoints",
    "InfoModel",
    "InvalidOperationError",
    "MediaNative",
    "MethodType",
    "NativeResponse",
    "Orchestrator",
    "Orchestrator38",
    "ResourceNotFoundError",
    "RuntimeInfo",
    "RuntimeEnvelope",
    "RuntimeEnvelope38",
    "ResponseType",
    "ResourceBinding",
    "ServiceError",
    "ServiceGateway",
    "ServiceGateway38",
    "ServiceOperation",
    "ServiceOperation38",
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
    "build_service_gateway38",
    "coerce_runtime_info",
    "user_id_by_key",
]
