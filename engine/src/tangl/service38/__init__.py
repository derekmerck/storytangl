"""Service38 orchestrator/gateway surface."""

from .api_endpoint import ApiEndpoint38, EndpointPolicy, ResourceBinding, WritebackMode
from .auth import UserAuthInfo, user_id_by_key
from .bootstrap import build_service_gateway38
from .gateway import GatewayExecuteOptions, ServiceGateway38
from .operations import ServiceOperation38
from .orchestrator import ExecuteOptions, Orchestrator38
from .rest_adapter import GatewayRequest38, GatewayRestAdapter38
from .response import (
    FragmentStream,
    InfoModel,
    MediaNative,
    NativeResponse,
    RuntimeInfo,
    coerce_runtime_info,
)

__all__ = [
    "ApiEndpoint38",
    "EndpointPolicy",
    "ExecuteOptions",
    "FragmentStream",
    "GatewayExecuteOptions",
    "GatewayRequest38",
    "GatewayRestAdapter38",
    "InfoModel",
    "MediaNative",
    "NativeResponse",
    "Orchestrator38",
    "RuntimeInfo",
    "ResourceBinding",
    "ServiceGateway38",
    "ServiceOperation38",
    "UserAuthInfo",
    "WritebackMode",
    "build_service_gateway38",
    "coerce_runtime_info",
    "user_id_by_key",
]
