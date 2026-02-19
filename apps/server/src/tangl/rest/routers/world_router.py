from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies38 import get_service_gateway38
from tangl.service.response.info_response import WorldInfo
from tangl.service38 import ServiceGateway38, ServiceOperation38


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    gateway: ServiceGateway38 = Depends(get_service_gateway38),
    world_id: str = Path(example="my_world"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> WorldInfo:
    """Return metadata describing ``world_id``."""

    try:
        return gateway.execute(
            ServiceOperation38.WORLD_INFO,
            world_id=world_id,
            render_profile=render_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc
