from fastapi import Depends, Query, Header, Body, Path

from tangl.config import settings
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import uuid_for_key, key_for_secret
from tangl.service import ServiceManager
from tangl.service.service_manager import RuntimeInfo, JournalEntry
from tangl.rest.app_service_manager import get_service_manager, get_user_locks
from .story_router import router as story_router
from .system_router import router as system_router
from .world_router import router as world_router


@story_router.put("/go", response_model=JournalEntry, response_model_exclude_none=True, tags=['Restricted'])
async def goto_story_block(
        service_manager: ServiceManager = Depends(get_service_manager),
        user_locks: dict = Depends(get_user_locks),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        block_id: UniqueLabel = Query(example="scene_1/block_1")):
    """
    Navigate directly to a specific block in the story (restricted)

    This endpoint updates the current story bookmark to the specified block.
    Forcing a block open will mark the story as 'dirty'.
    """
    user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    async with user_locks[user_id]:
        update = service_manager.goto_story_node(user_id, block_id)
        return update

@story_router.get("/info", response_model=RuntimeInfo, response_model_exclude_none=True, tags=['Restricted'])
async def inspect_story_node(
        service_manager: ServiceManager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        node_id: UniqueLabel = Query(example="scene_1/block_1") ):
    """
    Retrieve information about a specific node in the story (restricted)

    This endpoint provides information about the specified node.
    """
    user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    return service_manager.get_node_info(user_id, node_id)

@story_router.post("/check", response_model=RuntimeInfo, response_model_exclude_none=True, tags=['Restricted'])
async def check_expression(
        service_manager: ServiceManager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        expr: str = Body()):
    """
    Dynamically evaluate a expression in the current story (restricted)
    """
    user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    return service_manager.check_story_expr(user_id=user_id, condition=expr)

@story_router.post("/apply", response_model=dict, response_model_exclude_none=True, tags=['Restricted'])
def apply_effect(
        service_manager: ServiceManager = Depends(get_service_manager),
        user_locks: dict = Depends(get_user_locks),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        expr: str = Body()) -> RuntimeInfo:
    """
    Apply an effect expression in the current story (restricted)

    Directly manipulating the game state will mark the story as 'dirty'.
    """
    user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    with user_locks[user_id]:
        return service_manager.apply_story_expr(user_id, expr=expr)

@system_router.put("/reset", tags=["Restricted"])
async def reset_system(
        service_manager: ServiceManager = Depends(get_service_manager),
        # api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        hard=False):
    """
    Reset the system (restricted)

    This endpoint drops all worlds and reloads them. If the 'hard' parameter is set
    to True, it also discards all users and story data.
    """
    # user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    service_manager.reset_system(hard)

@world_router.get("/{world_id}/scenes", tags=['Restricted'])
def get_scene_list(
        service_manager: ServiceManager = Depends(get_service_manager),
        # api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        world_id: UniqueLabel = Path()) -> list:
    """
    List scenes in a world (restricted)
    """
    # user_id = uuid_for_key(api_key)
    # todo: need to verify user privilege level
    return service_manager.get_scene_list(world_id)
