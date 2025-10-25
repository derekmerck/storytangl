from abc import ABC, abstractmethod
from uuid import UUID

from tangl.type_hints import UniqueLabel
from tangl.story import StoryInfo
from tangl.story.world import WorldInfo, WorldList, WorldSceneList
from tangl.journal import JournalEntry
from tangl.user import UserInfo
from .runtime_info_model import RuntimeInfo
from .system_info_model import SystemInfo

MediaResponse = object

def public_endpoint(func):
    setattr(func, "public_endpoint", True)
    return func

def client_endpoint(func):
    # todo: need to check that user exists
    setattr(func, "client_endpoint", True)
    return func

def dev_endpoint(func):
    # todo: need to check that user exists and has proper flag
    setattr(func, "dev_endpoint", True)
    return func

class ServiceManagerAbc(ABC):

    ###########################################################################
    # Story Controller
    ###########################################################################

    # Client Functions

    @client_endpoint
    @abstractmethod
    def get_story_info(self, obj_id: UUID, **features) -> StoryInfo:
        ...

    @client_endpoint
    @abstractmethod
    def get_story_update(self, obj_id: UUID, section: int | str = -1) -> JournalEntry:
        ...

    @client_endpoint
    @abstractmethod
    def do_story_action(self, obj_id: UUID, *, action_id: UUID, payload: dict = None) -> JournalEntry:
        ...

    @client_endpoint
    @abstractmethod
    def get_story_media(self, obj_id: UUID, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    @abstractmethod
    def get_node_info(self, obj_id: UUID, node_id: UUID | UniqueLabel) -> RuntimeInfo:
        ...

    @dev_endpoint
    @abstractmethod
    def goto_story_node(self, obj_id: UUID, node_id: UUID | UniqueLabel) -> JournalEntry:
        ...

    @dev_endpoint
    @abstractmethod
    def check_story_expr(self, obj_id: UUID, expr: str ) -> RuntimeInfo:
        ...

    @dev_endpoint
    @abstractmethod
    def apply_story_expr(self, obj_id: UUID, expr: str ) -> RuntimeInfo:
        ...


    ###########################################################################
    # User Controller
    ###########################################################################

    @public_endpoint
    @abstractmethod
    def get_uuid_for_secret(self, secret: str) -> RuntimeInfo:
        ...

    @public_endpoint
    @abstractmethod
    def create_user(self, secret: str = None) -> RuntimeInfo:
        ...

    # Client Functions

    @client_endpoint
    @abstractmethod
    def update_user_secret(self, user_id: UUID, secret: str = None) -> RuntimeInfo:
        ...

    @client_endpoint
    @abstractmethod
    def drop_user(self, user_id: UUID) -> RuntimeInfo:
        ...

    @client_endpoint
    @abstractmethod
    def get_user_info(self, user_id: UUID) -> UserInfo:
        ...

    @client_endpoint
    @abstractmethod
    def create_story(self, user_id: UUID, world_id: UniqueLabel) -> JournalEntry:
        ...

    @client_endpoint
    @abstractmethod
    def drop_story(self, user_id: UUID, story_id: UUID) -> RuntimeInfo:
        ...

    @client_endpoint
    @abstractmethod
    def set_story(self, user_id: UUID, story_id: UUID) -> RuntimeInfo:
        ...


    ###########################################################################
    # World Controller
    ###########################################################################

    @public_endpoint
    @abstractmethod
    def get_world_list(self) -> WorldList:
        ...

    @public_endpoint
    @abstractmethod
    def get_world_info(self, world_id: UniqueLabel) -> WorldInfo:
        ...

    @public_endpoint
    @abstractmethod
    def get_world_media(self, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    @abstractmethod
    def get_scene_list(self, world_id: UniqueLabel) -> WorldSceneList:
        ...


    ###########################################################################
    # System Controller
    ###########################################################################

    @public_endpoint
    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        ...

    # Developer Functions

    @dev_endpoint
    @abstractmethod
    def reset_system(self, hard: bool = False) -> RuntimeInfo:
        ...
