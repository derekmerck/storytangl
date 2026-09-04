from __future__ import annotations

from fastapi import APIRouter, Depends, Query

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
    secret: str = Query(examples=["example-user-secret"]),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserSecret:
    """Derive the API key transport form of a recovery codename.

    ``secret`` is required. This endpoint only encodes a codename the caller
    already holds; it never mints one. Minting belongs to ``POST /user/create``
    with no secret, which rerolls while a codename is occupied and persists the
    resulting user. A public endpoint that minted without that occupancy check
    would hand out working keys for codenames already in use -- codenames are
    low-entropy bearer capabilities, so the derived key is the whole credential
    (issue #352).
    """

    _ = render_profile
    require_service_access("get_key_for_secret")
    return service_manager.get_key_for_secret(secret=secret)
