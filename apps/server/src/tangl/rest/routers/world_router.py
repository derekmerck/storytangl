from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator
from tangl.service.response.info_response import WorldInfo
from tangl.story.fabula.world import World


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    world_id: str = Path(example="my_world"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> WorldInfo:
    """Return metadata describing ``world_id``."""

    _ = render_profile  # Legacy path is transport/profile agnostic.
    try:
        world = World.get_instance(world_id)
        if world is None:
            raise ValueError
        return orchestrator.execute("WorldController.get_world_info", world=world)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc
