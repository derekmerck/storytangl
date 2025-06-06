from fastapi import APIRouter, Depends, Query, Header, Body

from tangl.config import settings
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import uuid_for_key, key_for_secret
from tangl.service import ServiceManager
from tangl.service.service_manager import UserInfo, JournalEntry, RuntimeInfo
from tangl.rest.app_service_manager import get_service_manager, get_user_locks
from .response_models import UserSecret

router = APIRouter(tags=['User'])

@router.get("/info", response_model=UserInfo)
async def get_user_info(
        service_manager: ServiceManager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None)):
    """
    Retrieve information about the specified user.

    In particular, this endpoint provides the current world_id for
    the user's story bookmark.
    """
    user_id = uuid_for_key(api_key)
    info = service_manager.get_user_info(user_id)
    return info

@router.post("/create", response_model=UserSecret)
async def create_user(
        service_manager: ServiceManager = Depends(get_service_manager),
        secret: str = Query(example=settings.client.secret, default=None)):
    """
    Create a new user and returns the api_key and secret.

    This endpoint creates a new user in the system.  This is a public endpoint.
    """
    # todo: this should set an auth cookie, too
    response = service_manager.create_user(secret)
    return UserSecret(user_secret=response.user_secret, user_id=response.user_id)

@router.put("/world", response_model=JournalEntry)
async def set_user_world(
        service_manager: ServiceManager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        world_id: UniqueLabel = Body()):
    user_id = uuid_for_key(api_key)
    service_manager.set_story(user_id, world_id)
    try:
        return service_manager.get_story_update(user_id)
    except KeyError:
        return service_manager.create_story(user_id, world_id)

# @router.get("/secret")
# async def check_user_secret(
#         user_id: Uid = Header(),
#         secret: str = Query(example=settings.client.secret, default=None) ):
#     """
#     Confirm that the user_id matches the secret and that the account is active.
#     Returns 200 on success, 401 on failure.
#     """
#     res = story_manager_api.check_user_secret(user_id, secret)
#     if res:
#         return 200
#     return 401


@router.put("/secret", response_model=UserSecret)
async def update_user_secret(
        service_manager: ServiceManager = Depends(get_service_manager),
        user_locks: dict = Depends(get_user_locks),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
        secret: str = Query(example=settings.client.secret, default=None)):
    """
    - Update secret for an existing user and return the new api key
    - If no secret is provided, a random secret is generated and returned with the new api key
    - Sets an auth cookie for dynamic assets
    - Client should provide the new key in headers on future calls
    """
    # todo: this should set an auth cookie, too
    user_id = uuid_for_key(api_key)
    with user_locks[user_id]:
        response = service_manager.update_user_secret(user_id, secret)
        # a new secret may have been generated if none was passed
        api_key = key_for_secret(response.user_secret)
        return UserSecret(
            user_secret=response.user_secret,
            api_key=api_key,
            user_id=response.user_id)

@router.delete("/drop")
async def drop_user(
        service_manager: ServiceManager = Depends(get_service_manager),
        api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None)):
    """
    Delete the current user.

    Typically, the client will follow up by creating a new user and
    registering a new api key
    """
    user_id = uuid_for_key(api_key)
    service_manager.drop_user(user_id)



