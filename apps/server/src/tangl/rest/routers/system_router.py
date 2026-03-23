from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from tangl.config import settings
from tangl.rest.dependencies_gateway import get_service_manager, require_service_access
from tangl.service import ServiceManager
from tangl.service.response import SystemInfo, UserSecret, WorldInfo


router = APIRouter(tags=["System"])


@router.get("/info")
async def get_system_info(
    service_manager: ServiceManager = Depends(get_service_manager),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> SystemInfo:
    """Return high-level information about the running service."""

    _ = render_profile
    require_service_access("get_system_info")
    return service_manager.get_system_info()


@router.get("/worlds")
async def get_worlds(
    service_manager: ServiceManager = Depends(get_service_manager),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> list[WorldInfo]:
    """List the available worlds registered with the service."""

    _ = render_profile
    require_service_access("list_worlds")
    return service_manager.list_worlds()


@router.get("/secret")
async def get_key_for_secret(
    service_manager: ServiceManager = Depends(get_service_manager),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserSecret:
    """Encode ``secret`` as an API key for clients."""

    _ = render_profile
    require_service_access("get_key_for_secret")
    return service_manager.get_key_for_secret(secret=secret)
