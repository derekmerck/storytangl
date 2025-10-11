from __future__ import annotations

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    world_id: str = Path(example="my_world"),
):
    """Return metadata describing ``world_id``."""

    try:
        return orchestrator.execute("WorldController.get_world_info", world_id=world_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found") from exc

