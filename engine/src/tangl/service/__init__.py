"""Legacy compatibility shim exposing service38 surface with lazy aliases."""

from __future__ import annotations

from importlib import import_module

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    # Legacy endpoint contract surface.
    "AccessLevel": ("tangl.service.api_endpoint", "AccessLevel"),
    "HasApiEndpoints": ("tangl.service.api_endpoint", "HasApiEndpoints"),
    "MethodType": ("tangl.service.api_endpoint", "MethodType"),
    "ResponseType": ("tangl.service.api_endpoint", "ResponseType"),
    # Primary v38 aliases.
    "ApiEndpoint": ("tangl.service38.api_endpoint", "ApiEndpoint38"),
    "Orchestrator": ("tangl.service38.orchestrator", "Orchestrator38"),
    # Explicit v38 exports.
    "ApiEndpoint38": ("tangl.service38.api_endpoint", "ApiEndpoint38"),
    "EndpointPolicy": ("tangl.service38.api_endpoint", "EndpointPolicy"),
    "ExecuteOptions": ("tangl.service38.orchestrator", "ExecuteOptions"),
    "FragmentStream": ("tangl.service38.response", "FragmentStream"),
    "GatewayExecuteOptions": ("tangl.service38.gateway", "GatewayExecuteOptions"),
    "GatewayRequest38": ("tangl.service38.rest_adapter", "GatewayRequest38"),
    "GatewayRestAdapter38": ("tangl.service38.rest_adapter", "GatewayRestAdapter38"),
    "InfoModel": ("tangl.service38.response", "InfoModel"),
    "MediaNative": ("tangl.service38.response", "MediaNative"),
    "NativeResponse": ("tangl.service38.response", "NativeResponse"),
    "Orchestrator38": ("tangl.service38.orchestrator", "Orchestrator38"),
    "ResourceBinding": ("tangl.service38.api_endpoint", "ResourceBinding"),
    "RuntimeInfo": ("tangl.service38.response", "RuntimeInfo"),
    "ServiceGateway38": ("tangl.service38.gateway", "ServiceGateway38"),
    "ServiceOperation38": ("tangl.service38.operations", "ServiceOperation38"),
    "UserAuthInfo": ("tangl.service38.auth", "UserAuthInfo"),
    "WritebackMode": ("tangl.service38.api_endpoint", "WritebackMode"),
    "coerce_runtime_info": ("tangl.service38.response", "coerce_runtime_info"),
    "user_id_by_key": ("tangl.service38.auth", "user_id_by_key"),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str):
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
