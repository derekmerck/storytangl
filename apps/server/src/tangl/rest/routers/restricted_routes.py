from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Path, Query

from tangl.service.response.info_response import RuntimeInfo
from tangl.config import settings
from tangl.rest.dependencies38 import get_service_adapter38, get_user_locks38
from tangl.service38 import GatewayRestAdapter38, ServiceOperation38
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret

from .story_router import router as story_router
from .system_router import router as system_router
from .world_router import router as world_router


def _call(
    adapter: GatewayRestAdapter38,
    operation: ServiceOperation38,
    /,
    *,
    user_id=None,
    render_profile: str = "raw",
    **params,
):
    return adapter.execute_operation(
        operation,
        user_id=user_id,
        render_profile=render_profile,
        **params,
    )


@story_router.put("/go", tags=["Restricted"])
async def goto_story_block(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks = Depends(get_user_locks38),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    block_id: UniqueLabel = Query(example="scene_1/block_1"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Jump the active frame to ``block_id``."""

    user_id = adapter.resolve_user_id(api_key)
    async with user_locks[user_id]:
        return _call(
            adapter,
            ServiceOperation38.STORY_JUMP,
            user_id=user_id,
            render_profile=render_profile,
            node_id=block_id,
        )


@story_router.get("/info", tags=["Restricted"])
async def inspect_story_node(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> RuntimeInfo:
    """Return diagnostic story information for the active user."""

    user_id = adapter.resolve_user_id(api_key)
    return _call(
        adapter,
        ServiceOperation38.STORY_STATUS,
        user_id=user_id,
        render_profile=render_profile,
    )


@story_router.post("/check", tags=["Restricted"])
async def check_expression() -> RuntimeInfo:
    """Expression inspection is not yet supported."""

    raise HTTPException(status_code=501, detail="Expression inspection is not available")


@story_router.post("/apply", tags=["Restricted"])
async def apply_effect() -> RuntimeInfo:
    """Direct state mutation is not supported in the orchestrated REST API."""

    raise HTTPException(status_code=501, detail="Direct story mutation is not available")


@system_router.put("/reset", tags=["Restricted"])
async def reset_system():
    """System resets are not wired through the orchestrator yet."""

    raise HTTPException(status_code=501, detail="System reset is not available")


@world_router.get("/{world_id}/scenes", tags=["Restricted"])
async def get_scene_list(world_id: UniqueLabel = Path()):
    """Scene listing is not yet exposed through the orchestrated REST API."""

    raise HTTPException(status_code=501, detail="Scene listings are not available")
