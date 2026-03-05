from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies38 import get_service_adapter38
from tangl.service38 import GatewayRestAdapter38, ServiceOperation38


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    world_id: str = Path(example="my_world"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> dict:
    """Return metadata describing ``world_id``."""
    try:
        result = adapter.execute_operation(
            ServiceOperation38.WORLD_INFO,
            render_profile=render_profile,
            world_id=world_id,
        )
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        if isinstance(result, dict):
            return result
        return {"value": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc
