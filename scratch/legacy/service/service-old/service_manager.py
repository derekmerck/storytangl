from contextlib import contextmanager
from uuid import UUID
import logging
import functools

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler
from tangl.utils.persistence import PersistenceManagerFactory
from tangl.utils.uuid_for_secret import uuid_for_secret
from tangl.story import Story, StoryHandler, StoryInfo
from tangl.story.world import World, WorldHandler, WorldInfo, WorldList, WorldSceneList
from tangl.journal import JournalHandler, JournalEntry
from tangl.user import User, UserHandler, UserInfo
from .response_handler import ResponseHandler
from .runtime_info_model import RuntimeInfo
from .system_handler import SystemHandler
from .system_info_model import SystemInfo
from .service_manager_abc import ServiceManagerAbc, public_endpoint, client_endpoint, dev_endpoint

MediaResponse = bytes | str

logger = logging.getLogger(__name__)

def handle_response(func):
    """
    The response handler will handle BaseResponse models and lists of BaseResponse,
    including xInfo models.  However, RuntimeInfo is ignored by the service manager,
    since the result is expected to be raw output.

    response params:
    - accepts_html: parses fields indicated as markdown fields into html
    - accepts_media_as_data: converts media inventory tags to PIL or binary python data objects
    """
    @functools.wraps(func)
    def wrapper(self, *args, response_params: dict = None, **kwargs):
        # response_params = kwargs.pop('response_params', {}) or {}
        response = func(self, *args, **kwargs)
        response_params = response_params or {}
        ResponseHandler.handle_response(response, **response_params)
        return response
    return wrapper

# todo: use decorator to automatically invoke the response handler on return?


class ServiceManager(BaseHandler, ServiceManagerAbc):

    def __init__(self):
        logger.debug("Creating pm")
        self.persistence = PersistenceManagerFactory.create_persistence_manager()

    @contextmanager
    def open_story(self, obj_id: UUID, write_back: bool = False) -> Story:
        with self.persistence.open(obj_id, write_back) as obj:

            if isinstance(obj, Story):
                story = obj
                user_id = story.user
                with self.persistence.open(user_id, write_back) as user:
                    # relink the user and story
                    story.user = user
                    yield story

            elif isinstance(obj, User):
                user = obj
                story_id = user.current_story_id
                with self.persistence.open(story_id, write_back) as story:
                    # relink the user and story
                    story.user = user
                    yield story

            # unlink the user and story to save separately
            if write_back:
                story.user = user.uid

    ###########################################################################
    # Story Controller
    ###########################################################################

    @client_endpoint
    @handle_response
    def get_story_info(self, obj_id: UUID) -> StoryInfo:
        with self.open_story(obj_id) as story:
            response = StoryHandler.get_story_info(story)
            return response

    @client_endpoint
    @handle_response
    def get_story_update(self, obj_id: UUID, *, section: int | str = -1) -> JournalEntry:
        with self.open_story(obj_id) as story:
            response = JournalHandler.get_journal_entry(story.journal, section)
            return response

    @client_endpoint
    @handle_response
    def do_story_action(self, obj_id: UUID, *,
                        action_id: UUID | UniqueLabel,
                        payload: dict = None) -> JournalEntry:
        with self.open_story(obj_id, write_back=True) as story:
            StoryHandler.do_action(story, action_id, payload=payload)
            response = JournalHandler.get_journal_entry(story.journal, -1)
            return response

    @client_endpoint
    def get_story_media(self, obj_id: UUID, *, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    def get_node_info(self, obj_id: UUID, *, node_id: UUID | UniqueLabel) -> RuntimeInfo:
        with self.open_story(obj_id) as story:
            node = story.get_node(node_id)
            info = node.model_dump()
            response = RuntimeInfo(
                job='read',
                story_id=story.uid,
                node_id=node.uid,
                result=info
            )
            return response

    @dev_endpoint
    @handle_response
    def goto_story_node(self, obj_id: UUID, *, node_id: UUID | UniqueLabel) -> JournalEntry:
        with self.open_story(obj_id, write_back=True) as story:
            StoryHandler.goto_node(story, node_id)
            response = JournalHandler.get_journal_entry(story.journal, -1)
            # could include a runtime response, suggesting get update or provide the update as a field
            return response

    @dev_endpoint
    def check_story_expr(self, obj_id: UUID, *, expr: str ) -> RuntimeInfo:
        with self.open_story(obj_id,) as story:
            result = StoryHandler.check_expr(story, expr)
            response = RuntimeInfo(
                job='read',
                story_id=story.uid,
                expr=expr,
                result=result
            )
            return response

    @dev_endpoint
    def apply_story_expr(self, obj_id: UUID, *, expr: str ) -> RuntimeInfo:
        with self.open_story(obj_id, write_back=True) as story:
            StoryHandler.apply_expr(story, expr)  # doesn't return anything
            response = RuntimeInfo(
                job='update',
                story_id=story.uid,
                expr=expr,
                result='OK'
            )
            return response


    ###########################################################################
    # User Controller
    ###########################################################################

    @public_endpoint
    def get_uuid_for_secret(self, secret: str) -> RuntimeInfo:
        user_id = uuid_for_secret(secret)
        response = RuntimeInfo(
            job='read',
            user_id=user_id,
            user_secret=secret,
            result='OK'
        )
        return response

    @public_endpoint
    def create_user(self, *, secret: str = None) -> RuntimeInfo:
        # this is a public endpoint if we want to allow users to self-initialize
        logger.debug("Creating user")
        user = UserHandler.create_user(secret)
        self.persistence.save(user)
        # could return the user info object?
        response = RuntimeInfo(
            job='create',
            user_id=user.uid,
            user_secret=user.secret,
            result='OK'
        )
        return response

    @client_endpoint
    def update_user_secret(self, user_id: UUID, *, secret: str = None) -> RuntimeInfo:
        # todo: need to delete old user from persistence, update all their stories with the new id, and add the new user, more complicated than this
        with self.persistence.open(user_id, write_back=True) as user:
            UserHandler.update_user_secret(user, secret)
            # could return an updated user info object?
            response = RuntimeInfo(
                job='update',
                user_id=user.uid,
                user_secret=user.secret,
                result='OK'
            )
            return response

    @client_endpoint
    def drop_user(self, user_id: UUID) -> RuntimeInfo:
        self.persistence.remove(user_id)
        response = RuntimeInfo(
            job="drop",
            user_id=user_id,
            result="OK")
        return response

    @client_endpoint
    def get_user_info(self, user_id: UUID) -> UserInfo:
        if user_id not in self.persistence:
            return
        with self.persistence.open(user_id) as user:
            response = UserHandler.get_user_info(user)
        return response

    @client_endpoint
    @handle_response
    def create_story(self, user_id: UUID, *, world_id: UniqueLabel) -> JournalEntry:
        world = World.get_instance(world_id)
        with self.persistence.open(user_id, write_back=True) as user:
            story = WorldHandler.create_story(world, user=user)
            story.enter()
            # create a journal, create a history ...
            self.persistence.save(story)
            UserHandler.set_current_story(user, story)
            response = JournalHandler.get_journal_entry(story.journal)
            # todo: could include a runtime response, suggesting get update or provide the update as a field, doing or creating should maybe just return a runtime response, then the client should request an update
            return response

    @client_endpoint
    def drop_story(self, user_id: UUID, *, story_id: UUID) -> RuntimeInfo:
        # todo: this is not right, do we pass it a world_id as the argument? can a user only have one open story per world?
        with self.persistence.open(user_id, write_back=True) as user:
            UserHandler.set_current_story(user, None)
        self.persistence.remove(story_id)
        response = RuntimeInfo(
            job="drop",
            user_id=user_id,
            story_id=story_id,
            result="OK")
        return response

    @client_endpoint
    def set_story(self, user_id: UUID, *, story_id: UUID) -> RuntimeInfo:
        # todo: this is not right, do we pass it a world_id as the argument? can a user only have one open story per world?
        with self.persistence.open(user_id, write_back=True) as user:
            UserHandler.set_current_story(user, story_id)
            response = RuntimeInfo(
                job="update",
                user_id=user_id,
                story_id=user.current_story_id,
                result="OK")
            return response


    ###########################################################################
    # World Controller
    ###########################################################################

    @public_endpoint
    def get_world_list(self) -> WorldList:
        response = WorldHandler.get_world_list()
        return response

    @public_endpoint
    @handle_response
    def get_world_info(self, world_id: UniqueLabel) -> WorldInfo:
        world = World.get_instance(world_id)
        response = WorldHandler.get_world_info(world)
        return response

    @public_endpoint
    def get_world_media(self, media_id: UUID) -> MediaResponse:
        ...

    # Developer Functions

    @dev_endpoint
    def get_scene_list(self, world_id: UniqueLabel) -> WorldSceneList:
        world = World.get_instance(world_id)
        response = WorldHandler.get_scene_list(world)
        return response


    ###########################################################################
    # System Controller
    ###########################################################################

    @public_endpoint
    @handle_response
    def get_system_info(self) -> SystemInfo:
        return SystemHandler.get_system_info()

    # Developer Functions

    @dev_endpoint
    def reset_system(self, hard: bool = False) -> RuntimeInfo:
        SystemHandler.reset_system(hard=hard)
        response = RuntimeInfo(
            job='update',
            expr='system reset',
            result='OK'
        )
        return response
