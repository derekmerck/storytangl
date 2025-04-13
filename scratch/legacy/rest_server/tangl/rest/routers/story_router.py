from fastapi import APIRouter, Header, Body, Query, Depends

from tangl.config import settings
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import uuid_for_key, key_for_secret
from tangl.service.request_models import ActionRequest
from tangl.service.service_manager import JournalEntry, StoryInfo
from tangl.rest.app_service_manager import get_service_manager, get_user_locks

router = APIRouter(tags=['Story'])

@router.get("/update", response_model=JournalEntry, response_model_exclude_none=True)
async def get_story_update(
        service_manager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None)):
    """
    Retrieve the current story update for this user.

    This endpoint provides the current status of the story, including the
    block of text currently being displayed, any actions available to the
    user, and any media associated with the current state of the story.
    """
    user_id = uuid_for_key(api_key)
    update = service_manager.get_story_update(user_id)
    return update

@router.post("/do", response_model=JournalEntry, response_model_exclude_none=True)
async def do_story_action(
        service_manager = Depends(get_service_manager),
        user_locks = Depends(get_user_locks),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        action: ActionRequest = Body() ):
    """
    Do a story action and retrieve the current story update for this user.

    This endpoint allows a client to submit a story action, then generates an
    update and provides the current status of the story, including the
    block of text currently being displayed, any actions available to the
    user, and any media associated with the current state of the story.
    """
    user_id = uuid_for_key(api_key)
    async with user_locks[user_id]:
        payload = action.payload or {}
        service_manager.do_story_action(action_id=action.uid, **payload)
        update = service_manager.get_story_update(user_id)
        return update

# todo: add and test support for timeout
# from asyncio.exceptions import TimeoutError
#
# async def do_story_action(user_id: Uid = Header(default=None), action: ActionRequest = Body()):
#     try:
#         async with asyncio.wait_for(locks[user_id].acquire(), timeout=5): # 5 seconds timeout
#             payload = action.payload or {}
#             story_manager_api.do_story_action(action_id=action.uid, **payload)
#             update = story_manager_api.get_story_update(user_id)
#             update = deep_md(update)
#             return update
#     except TimeoutError:
#         # Handle the timeout exception as needed (e.g., return an error response)
#         ...
#     finally:
#         if locks[user_id].locked():
#             locks[user_id].release()


@router.get("/status", response_model=StoryInfo, response_model_exclude_none=True)
async def get_story_status(
        service_manager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        features: UniqueLabel = Query(default=None)):
    """
    This endpoint retrieves general features describing the overall story
    progression, such as the story name, scene, player stats, maps, inventory,
    etc.

    The features that can be requested vary by story-world and according to client
    UI capabilities.
    """
    user_id = uuid_for_key(api_key)
    status = service_manager.get_story_status(user_id, features)
    return status


@router.delete("/drop", response_model=JournalEntry, response_model_exclude_none=True)
async def reset_story(
        service_manager=Depends(get_service_manager),
        user_locks=Depends(get_user_locks),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None)):
    user_id = uuid_for_key(api_key)
    async with user_locks[user_id]:
        current_world_id = service_manager.get_current_world_id(user_id)
        service_manager.remove_story(user_id, current_world_id)
        return service_manager.create_story(user_id, current_world_id)
