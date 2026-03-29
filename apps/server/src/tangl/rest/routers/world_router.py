from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies_gateway import get_service_manager, require_service_access
from tangl.service import ServiceManager
from tangl.service.response import WorldInfo


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
