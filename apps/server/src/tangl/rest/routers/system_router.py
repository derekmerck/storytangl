from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from tangl.config import settings
from tangl.rest.dependencies38 import get_service_gateway38
from tangl.service.response.info_response.user_info import UserSecret
from tangl.service.response.info_response import SystemInfo
from tangl.service38 import ServiceGateway38, ServiceOperation38
from tangl.utils.hash_secret import key_for_secret


router = APIRouter(tags=["System"])


def _call(
    gateway: ServiceGateway38,
    operation: ServiceOperation38,
    /,
    *,
    render_profile: str = "raw",
    **params: Any,
) -> Any:
    return gateway.execute(operation, render_profile=render_profile, **params)


def _serialize(value: Any) -> Any:
    """Convert native responses into JSON-friendly payloads."""

    from uuid import UUID

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, set):
        return sorted((_serialize(item) for item in value), key=str)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        try:
            return _serialize(value.model_dump(mode="python"))
        except TypeError:
            return repr(value)
    return value


@router.get("/info")
async def get_system_info(
    gateway: ServiceGateway38 = Depends(get_service_gateway38),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> SystemInfo:
    """Return high-level information about the running service."""

    status = _call(
        gateway,
        ServiceOperation38.SYSTEM_INFO,
        render_profile=render_profile,
    )
    if hasattr(status, "guide_url"):
        setattr(status, "guide_url", "/guide")
    elif isinstance(status, dict):
        status.setdefault("guide_url", "/guide")
    return _serialize(status)


@router.get("/worlds")
async def get_worlds(
    gateway: ServiceGateway38 = Depends(get_service_gateway38),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> list[dict[str, object]]:
    """List the available worlds registered with the service."""

    return _serialize(
        _call(
            gateway,
            ServiceOperation38.WORLD_LIST,
            render_profile=render_profile,
        )
    )


@router.get("/secret")
async def get_key_for_secret(
    gateway: ServiceGateway38 = Depends(get_service_gateway38),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserSecret:
    """Encode ``secret`` as an API key for clients."""

    info = _call(
        gateway,
        ServiceOperation38.USER_KEY,
        render_profile=render_profile,
        secret=secret,
    )
    api_key = getattr(info, "api_key", None) or key_for_secret(secret)
    secret_value = getattr(info, "secret", secret)
    # user_id = getattr(info, "user_id", None)
    return UserSecret(user_secret=secret_value, api_key=api_key)
