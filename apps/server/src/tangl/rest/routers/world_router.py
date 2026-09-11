from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from tangl.rest.dependencies_gateway import get_service_manager, require_service_access
from tangl.presentation.projection import ProjectedState
from tangl.service import ServiceManager
from tangl.service.response import PreflightReport


router = APIRouter(tags=["World"])


@router.get("/{world_id}/info")
async def get_world_info(
    service_manager: ServiceManager = Depends(get_service_manager),
    world_id: str = Path(examples=["my_world"]),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
    channels: str | None = Query(
        default=None,
        description="Comma-separated exact public world-info channel ids.",
    ),
) -> ProjectedState:
    """Discover or retrieve public projected metadata for ``world_id``."""

    _ = render_profile
    require_service_access("get_world_info")
    try:
        selected = (
            [part.strip() for part in channels.split(",") if part.strip()]
            if channels
            else []
        )
        return service_manager.get_world_info(world_id=world_id, channels=selected)
    except ValueError as exc:
        if str(exc).startswith("Unknown info channel"):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
