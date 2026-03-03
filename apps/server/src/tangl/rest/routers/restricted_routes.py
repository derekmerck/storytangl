from __future__ import annotations

from fastapi import Body, Depends, Header, HTTPException, Path, Query
from pydantic import BaseModel

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator, get_user_locks
from tangl.rest.dependencies38 import get_service_adapter38, resolve_user_auth38
from tangl.service import Orchestrator
from tangl.service.response import RuntimeInfo
from tangl.service38 import GatewayRestAdapter38
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret

from .story_router import router as story_router
from .system_router import router as system_router
from .world_router import router as world_router


class DebugExprRequest(BaseModel):
    expr: str
    node_id: UniqueLabel | None = None


def _call_legacy(
    orchestrator: Orchestrator,
    endpoint_name: str,
    /,
    *,
    user_id=None,
    **params,
):
    kwargs = dict(params)
    if user_id is not None:
        kwargs["user_id"] = user_id
    return orchestrator.execute(endpoint_name, **kwargs)


@story_router.put("/go", tags=["Restricted"])
async def goto_story_block(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    block_id: UniqueLabel = Query(example="scene_1/block_1"),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Jump the active frame to ``block_id`` via the legacy orchestrator path."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    async with user_locks[user_auth.user_id]:
        return _call_legacy(
            orchestrator,
            "RuntimeController.jump_to_node",
            user_id=user_auth.user_id,
            node_id=block_id,
        )


@story_router.get("/inspect", tags=["Restricted"])
async def inspect_story_node(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
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
) -> RuntimeInfo:
    """Return debug inspection info for the active node (or a specific node)."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    async with user_locks[user_auth.user_id]:
        return _call_legacy(
            orchestrator,
            "RuntimeController.get_node_info",
            user_id=user_auth.user_id,
            node_id=node_id,
        )


@story_router.post("/check", tags=["Restricted"])
async def check_expression(
    request: DebugExprRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> RuntimeInfo:
    """Evaluate a debug expression in the active story context."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    async with user_locks[user_auth.user_id]:
        return _call_legacy(
            orchestrator,
            "RuntimeController.check_expr",
            user_id=user_auth.user_id,
            expr=request.expr,
            node_id=request.node_id,
        )


@story_router.post("/apply", tags=["Restricted"])
async def apply_effect_post(
    request: DebugExprRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> RuntimeInfo:
    """Apply a debug expression in the active story context."""
    _ = render_profile
    user_auth = resolve_user_auth38(api_key, adapter=adapter)
    async with user_locks[user_auth.user_id]:
        return _call_legacy(
            orchestrator,
            "RuntimeController.apply_effect",
            user_id=user_auth.user_id,
            expr=request.expr,
            node_id=request.node_id,
        )


@story_router.put("/apply", tags=["Restricted"])
async def apply_effect_put(
    request: DebugExprRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        example=key_for_secret(settings.client.secret),
        default=None,
        alias="X-API-Key",
    ),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> RuntimeInfo:
    """Compatibility alias for :route:`POST /story/apply`."""
    return await apply_effect_post(
        request=request,
        orchestrator=orchestrator,
        adapter=adapter,
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
