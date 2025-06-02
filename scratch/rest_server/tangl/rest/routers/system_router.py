from fastapi import APIRouter, Query, Depends

from tangl.config import settings
from tangl.utils.uuid_for_secret import key_for_secret
from tangl.service import ServiceManager
from tangl.service.service_manager import SystemInfo, WorldInfo, WorldList
from tangl.rest.app_service_manager import get_service_manager
from .response_models import UserSecret

router = APIRouter(tags=['System'])

@router.get("/info", response_model=SystemInfo)
async def get_system_info(
        service_manager: ServiceManager = Depends(get_service_manager) ):
    """
    Retrieve the current status of the system.

    This endpoint provides information about the system status, including the
    uptime, a media url for info, and the url for the guide, if applicable.
    """
    status = service_manager.get_system_info()
    status.guide_url = "/guide"
    return status

@router.get("/worlds", response_model=WorldList)
async def get_worlds(
        service_manager: ServiceManager = Depends(get_service_manager)):
    """
    Retrieve a list of the available worlds.

    This is a public endpoint that gives the ids for all the playable
    worlds that this server knows about.
    """
    worlds = service_manager.get_world_list()
    # print( worlds )
    return worlds

@router.get("/secret", response_model=UserSecret)
async def get_key_for_secret(
        service_manager: ServiceManager = Depends(get_service_manager),
        secret: str = Query(example=settings.client.secret, default=None)):
    """
    Retrieve a user key based on a secret.

    This is a public endpoint that enables users to restore credentials.
    """
    # todo: this should set an auth cookie, too
    response = service_manager.get_uuid_for_secret(secret)
    api_key = key_for_secret(response.user_secret)
    # a new secret may have been generated if none was passed
    return UserSecret(
        user_secret=response.user_secret,
        api_key=api_key,
        user_id=response.user_id)
