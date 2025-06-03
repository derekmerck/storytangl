import asyncio
from collections import defaultdict
from uuid import UUID
import logging

from tangl.config import settings
from tangl.service import ServiceManager

logger = logging.getLogger(__name__)
logger.debug("setting up app service manager")

service_manager = ServiceManager()

# todo: this should actually decide whether to use a stand-alone service manager
#       or create a relay service manager using tangl.server.RelayServiceManager
#       based on settings

# def setup_worlds():
#     # todo: not quite right yet
#     # Force the world to load and create a story if it doesn't exist
#     world_id = settings.client.default_world
#     importlib.import_module(world_id)
#
#     response = service_manager.create_story(user_id, world_id)
#     service_manager.set_current_story_id(user_id, world_id)
#     logger.debug(response)

def get_service_manager() -> ServiceManager:
    return service_manager

def setup_user_credentials(service_manager: ServiceManager) -> UUID:
    secret = settings.client.secret
    user_id = service_manager.get_uuid_for_secret(secret).user_id
    logger.debug(f"user_id: {user_id}")
    if not service_manager.get_user_info(user_id):
        result = service_manager.create_user(secret=secret)
        assert user_id == result.user_id
    return user_id

user_id = setup_user_credentials(service_manager)

def get_user_id() -> UUID:
    return user_id
