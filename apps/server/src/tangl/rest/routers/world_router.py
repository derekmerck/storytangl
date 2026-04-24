from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies_gateway import get_service_manager, require_service_access
from tangl.service import ServiceManager
from tangl.service.response import PreflightReport, WorldInfo


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    service_manager: ServiceManager = Depends(get_service_manager),
    world_id: str = Path(example="my_world"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> WorldInfo:
    """Return metadata describing ``world_id``."""

    _ = render_profile
    require_service_access("get_world_info")
    try:
        return service_manager.get_world_info(world_id=world_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc


@router.get("/{world_id}/preflight")
async def preflight_world(
    service_manager: ServiceManager = Depends(get_service_manager),
    world_id: str = Path(examples=["my_world"]),
) -> PreflightReport:
    """Return non-mutating authoring diagnostics for ``world_id``."""

    require_service_access("preflight_world")
    try:
        return service_manager.preflight_world(world_id=world_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc
