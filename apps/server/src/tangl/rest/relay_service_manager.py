from uuid import UUID
import logging
from typing import Literal

from requests import Session

from tangl.config import settings
from tangl.type_hints import UniqueLabel
from tangl.story import StoryInfo
from tangl.story.world import WorldInfo, WorldList, WorldSceneList
from tangl.core.solver import JournalFragment
from tangl.user import UserInfo
from tangl.service.service_manager_abc import ServiceManagerAbc, RuntimeInfo, SystemInfo, MediaResponse, public_endpoint, dev_endpoint, client_endpoint

logger = logging.getLogger(__name__)

DEFAULT_API_URL = settings.server.url
API_ROUTER = Literal['story', 'user', 'world', 'system']


class RelayServiceManager(ServiceManagerAbc):
    """
    Implements ServiceManager, but uses python-requests to delegate function
    calls a remote server.

    Use to convert stand-alone apps with their own service manager into network
    clients.
    """

    def _url(self, router: API_ROUTER, resource: str):
        return f"{self.api_url}/{router}/{resource}"

    def relay_get(self, router, resource, **params):
        return self.session.get(self._url(router, resource), params=params)

    def relay_put(self, router, resource, **params):
        return self.session.put(self._url(router, resource), params=params)

    def relay_delete(self, router, resource, **params):
        return self.session.delete(self._url(router, resource), params=params)

    def relay_post(self, router, resource, **data):
        return self.session.post(self._url(router, resource), json=data)

    def __init__(self,
                 api_url: str = DEFAULT_API_URL,
                 user_id: UUID = None):
        self.api_url = api_url
        self.session = Session()
        # todo: include the api-key in the session headers if single-user
        super().__init__()

    ###########################################################################
    # Story Controller
    ###########################################################################

    # Client Functions

    @client_endpoint
    def get_story_info(self, obj_id: UUID, **features) -> StoryInfo:
        result = self.relay_get("story", "info", **features)
        # todo: returns list
        return StoryInfo(**result.json())

    @client_endpoint
    def get_story_update(self, obj_id: UUID, section: int | str = -1) -> JournalEntry:
        result = self.relay_get("story", "update", section=section)
        # todo: returns list
        return JournalEntry(**result.json())

    @client_endpoint
    def do_story_action(self, obj_id: UUID, *, action_id: UUID, payload: dict = None) -> JournalEntry:
        result = self.relay_post("story", "action",
                                 action_id=action_id, payload=payload )
        # todo: returns list
        return JournalEntry(**result.json())

    @client_endpoint
    def get_story_media(self, obj_id: UUID, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    def get_node_info(self, obj_id: UUID, node_id: UUID | UniqueLabel) -> RuntimeInfo:
        result = self.relay_get("story", "inspect", node_id = node_id)
        return RuntimeInfo(**result.json())

    @dev_endpoint
    def goto_story_node(self, obj_id: UUID, node_id: UUID | UniqueLabel) -> JournalEntry:
        result = self.relay_put("story", "go", node_id = node_id)
        # todo: returns list
        return JournalEntry(**result.json())

    @dev_endpoint
    def check_story_expr(self, obj_id: UUID, expr: str ) -> RuntimeInfo:
        result = self.relay_post("story", "check", expr = expr)
        return RuntimeInfo(**result.json())

    @dev_endpoint
    def apply_story_expr(self, obj_id: UUID, expr: str ) -> RuntimeInfo:
        result = self.relay_put("story", "apply", expr = expr)
        return RuntimeInfo(**result.json())


    ###########################################################################
    # User Controller
    ###########################################################################

    @public_endpoint
    def get_key_for_secret(self, secret: str) -> RuntimeInfo:
        result = self.relay_post("user", "key", secret = secret)
        return RuntimeInfo(**result.json())

    @public_endpoint
    def create_user(self, secret: str = None) -> RuntimeInfo:
        result = self.relay_post("user", "create", secret = secret)
        return RuntimeInfo(**result.json())

    # Client Functions

    @client_endpoint
    def update_user_secret(self, user_id: UUID, secret: str = None) -> RuntimeInfo:
        result = self.relay_put("user", "update", secret = secret)
        return RuntimeInfo(**result.json())

    @client_endpoint
    def drop_user(self, user_id: UUID) -> RuntimeInfo:
        result = self.relay_delete("user", "drop", user_id = user_id)
        return RuntimeInfo(**result.json())

    @client_endpoint
    def get_user_info(self, user_id: UUID) -> UserInfo:
        result = self.relay_get("user", "info", user_id = user_id)
        return UserInfo(**result.json())

    @client_endpoint
    def create_story(self, user_id: UUID, world_id: UniqueLabel) -> JournalEntry:
        result = self.relay_post("user", "story", world_id = world_id)
        # todo: returns list
        return JournalEntry(**result.json())

    @client_endpoint
    def drop_story(self, user_id: UUID, story_id: UUID) -> RuntimeInfo:
        result = self.relay_delete("user", "story", story_id = story_id )
        return RuntimeInfo(**result.json())

    @client_endpoint
    def set_story(self, user_id: UUID, story_id: UUID) -> RuntimeInfo:
        result = self.relay_put("user", "story", story_id = story_id )
        return RuntimeInfo(**result.json())


    ###########################################################################
    # World Controller
    ###########################################################################

    @public_endpoint
    def get_world_list(self) -> WorldList:
        result = self.relay_get("world", "ls")
        # todo: returns list
        return WorldList(**result.json())

    @public_endpoint
    def get_world_info(self, world_id: UniqueLabel) -> WorldInfo:
        result = self.relay_get("world", "info", world_id = world_id)
        return WorldInfo(**result.json())

    @public_endpoint
    def get_world_media(self, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    def get_scene_list(self, world_id: UniqueLabel) -> WorldSceneList:
        result = self.relay_get("world", "scenes", world_id = world_id)
        # todo: returns list
        return WorldSceneList(**result.json())


    ###########################################################################
    # System Controller
    ###########################################################################

    @public_endpoint
    def get_system_info(self) -> SystemInfo:
        result = self.relay_get("system", "info")
        return SystemInfo(**result.json())

    # Developer Functions

    @dev_endpoint
    def reset_system(self, hard: bool = False) -> RuntimeInfo:
        result = self.relay_put("system", "reset", hard = hard)
        return RuntimeInfo(**result.json())
