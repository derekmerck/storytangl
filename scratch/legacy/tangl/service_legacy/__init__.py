"""Legacy compatibility shim exposing switchable service surfaces."""

from __future__ import annotations

import os
from importlib import import_module
from typing import Any


_V38_VALUES = {"1", "true", "yes", "on", "v38", "new"}
_LEGACY_VALUES = {"0", "false", "no", "off", "legacy", "old"}


def _load(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


def _pick(
    symbol: str,
    legacy_target: tuple[str, str],
    v38_target: tuple[str, str],
    *,
    default: str = "v38",
):
    raw_value = os.getenv(
        f"TANGL_SHIM_SERVICE_{symbol}",
        os.getenv("TANGL_SHIM_SERVICE_DEFAULT", default),
    )
    selected = str(raw_value).strip().lower()
    if selected in _LEGACY_VALUES:
        return _load(*legacy_target)
    if selected in _V38_VALUES:
        return _load(*v38_target)
    raise ValueError(
        f"Invalid shim value '{raw_value}' for TANGL_SHIM_SERVICE_{symbol}. "
        f"Use one of {sorted(_LEGACY_VALUES | _V38_VALUES)}."
    )


_DYNAMIC_EXPORT_MAP: dict[str, tuple[tuple[str, str], tuple[str, str], str]] = {
    "ApiEndpoint": (
        ("tangl.service.api_endpoint", "ApiEndpoint"),
        ("tangl.service38.api_endpoint", "ApiEndpoint38"),
        "v38",
    ),
    "Orchestrator": (
        ("tangl.service.orchestrator", "Orchestrator"),
        ("tangl.service38.orchestrator", "Orchestrator38"),
        "v38",
    ),
}

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    # Legacy endpoint contract surface.
    "AccessLevel": ("tangl.service.api_endpoint", "AccessLevel"),
    "HasApiEndpoints": ("tangl.service.api_endpoint", "HasApiEndpoints"),
    "MethodType": ("tangl.service.api_endpoint", "MethodType"),
    "ResponseType": ("tangl.service.api_endpoint", "ResponseType"),
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

__all__ = sorted(set(_EXPORT_MAP) | set(_DYNAMIC_EXPORT_MAP))


def __getattr__(name: str):
    dynamic_target = _DYNAMIC_EXPORT_MAP.get(name)
    if dynamic_target is not None:
        legacy_target, v38_target, default = dynamic_target
        value = _pick(name.upper(), legacy_target, v38_target, default=default)
        globals()[name] = value
        return value

    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
