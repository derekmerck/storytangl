from __future__ import annotations

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator
from tangl.service.response.info_response import WorldInfo


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    world_id: str = Path(example="my_world"),
) -> WorldInfo:
    """Return metadata describing ``world_id``."""

    # todo: need to fix this, should dereference world in the controller preprocessor
    #       preprocessors are not getting called or world_id is not being passed bc
    #       its not in the sig?

    try:
        from tangl.story.fabula import World
        return orchestrator.execute("WorldController.get_world_info", world=World.get_instance(world_id))
        # return orchestrator.execute("WorldController.get_world_info", world_id=world_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc

