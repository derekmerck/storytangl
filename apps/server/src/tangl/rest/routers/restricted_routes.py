from __future__ import annotations

from typing import Any

from fastapi import Body, Depends, Header, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tangl.config import settings
from tangl.rest.dependencies_gateway import (
    get_user_locks,
    resolve_user_auth,
)
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret

from .story_router import router as story_router
from .system_router import router as system_router
from .world_router import router as world_router


class DebugExprRequest(BaseModel):
    expr: str
    node_id: UniqueLabel | None = None


def _not_implemented_response(endpoint_name: str) -> JSONResponse:
    """Return a stable 501 payload for deferred debug/restricted endpoints."""
    return JSONResponse(
        status_code=501,
        content={
            "status": "error",
            "code": "NOT_IMPLEMENTED",
            "message": f"{endpoint_name} is deferred during v38 cutover.",
        },
    )


@story_router.put("/go", tags=["Restricted"])
async def goto_story_block(
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    block_id: UniqueLabel = Query(example="scene_1/block_1"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Jump the active frame to ``block_id``."""
    user_auth = resolve_user_auth(api_key)
    async with user_locks[user_auth.user_id]:
        _ = (block_id, render_profile)
        return _not_implemented_response("story/go")


@story_router.get("/inspect", tags=["Restricted"])
async def inspect_story_node(
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    node_id: UniqueLabel | None = Query(
        default=None,
        description="Optional node identifier; defaults to current cursor node.",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> Any:
    """Return debug inspection info for the active node (or a specific node)."""
    user_auth = resolve_user_auth(api_key)
    async with user_locks[user_auth.user_id]:
        _ = (node_id, render_profile)
        return _not_implemented_response("story/inspect")


@story_router.post("/check", tags=["Restricted"])
async def check_expression(
    request: DebugExprRequest = Body(...),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> Any:
    """Evaluate a debug expression in the active story context."""
    user_auth = resolve_user_auth(api_key)
    async with user_locks[user_auth.user_id]:
        _ = (request, render_profile)
        return _not_implemented_response("story/check")


@story_router.post("/apply", tags=["Restricted"])
async def apply_effect_post(
    request: DebugExprRequest = Body(...),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> Any:
    """Apply a debug expression in the active story context."""
    user_auth = resolve_user_auth(api_key)
    async with user_locks[user_auth.user_id]:
        _ = (request, render_profile)
        return _not_implemented_response("story/apply")


@story_router.put("/apply", tags=["Restricted"])
async def apply_effect_put(
    request: DebugExprRequest = Body(...),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> Any:
    """Compatibility alias for :route:`POST /story/apply`."""
    return await apply_effect_post(
        request=request,
        user_locks=user_locks,
        api_key=api_key,
        render_profile=render_profile,
    )


@system_router.put("/reset", tags=["Restricted"])
async def reset_system():
    """System resets are not wired through the orchestrator yet."""
    raise HTTPException(status_code=501, detail="System reset is not available")


@world_router.get("/{world_id}/scenes", tags=["Restricted"])
async def get_scene_list(world_id: UniqueLabel = Path()):
    """Scene listing is not yet exposed through the orchestrated REST API."""
    _ = world_id
    raise HTTPException(status_code=501, detail="Scene listings are not available")
