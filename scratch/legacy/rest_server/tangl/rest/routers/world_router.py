from fastapi import APIRouter, HTTPException, Depends, Path

from tangl.service import ServiceManager
from tangl.service.service_manager import WorldInfo
from tangl.rest.app_service_manager import get_service_manager

router = APIRouter(tags=['World'])


@router.get("/{world_id}/info", response_model=WorldInfo, response_model_exclude_none=True)
async def get_world_info(
        service_manager: ServiceManager = Depends(get_service_manager),
        world_id: str = Path(example="my_world")):
    """
    Retrieve info about the specified world.

    This endpoint provides a mapping of world-specific metadata like description, title,
    authors, banner media, etc.
    """
    try:
        info = service_manager.get_world_info(world_id)
        return info
    except KeyError:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

