import contextlib

from typing import Callable
from logging import getLogger

from tangl.type_hints import Uid, UniqueLabel

# handlers
from tangl.graph import GraphStructuringHandler
from tangl.story import StoryHandler
from tangl.user import UserHandler
from tangl.world import WorldHandler
from tangl.persistence import PersistenceManagerFactory
from .story_persistence_manager import StoryPersistenceManager
from .system_handler import SystemHandler
from .response_handler import ResponseHandler

# request models
from .request_models import ActionRequest

# response models
from tangl.story import Story, StoryStatus, NodeInfo, JournalStoryUpdate
JournalEntry = list[JournalStoryUpdate]
from tangl.user import UserInfo, UserSecret
from tangl.world import WorldInfo, WorldList, WorldSceneList
from .response_models import SystemInfo, RuntimeInfo

logger = getLogger("tangl.service")

# todo: add service plugin manager with
#   - on_handle_response(call, computed response)
#   - need a response handler that can call registered formatters (markdown, media deref, plugins etc)

class ServiceManager:
    """
    A persistence manager with an extra stage (output formatting) and a wrapper
    around story, user, world, system service handlers. It organizes interactions
    between the service layer apis, the domain layer story and user apis, and the
    data layer.

    Presentation-layer clients and servers can use the service manager api to specify
    stories and execute api methods or get data from them.

    **Backend** the ServiceManager can use any storage backend that implements MutableMapping,
    such as those provided by `tangl.persistence.storage`.

    **Concurrency**: The`do_story_action`, `goto_story_node`, `apply_story_effect`,
    use a read-write story manager context, so they should be locked for atomicity
    when used in an asynchronous context.  `create`, `drop`, and `update` functions
    should also be locked for their duration.

    **Clients**: This package also includes a `FastApi` REST endpoint server and `cmd2`
    interactive cli that use the service manager api to interact the game logic.

    This is a complex class that covers a lot of functionality by 'gluing' the
    various component api's together.

    API v2 includes 21 methods divided into 4 zones: public, story, user, and restricted.

    - Public calls are stateless and do not require a context.
    - Story calls are stateful, they interrogate or advance a game context.
    - User Account calls can be used to manage the player's account.
    - The restricted API methods can be used for testing and direct access to a game context.
    """

    def __init__(self,
                 persistence_manager: StoryPersistenceManager = None,
                 response_handler: Callable = None):

        if persistence_manager is None:
            persistence_manager = PersistenceManagerFactory.create_persistence_manager(
                                            manager_cls=StoryPersistenceManager,
                                            structuring=GraphStructuringHandler)
        self.persistence_manager = persistence_manager

        if response_handler is None:
            response_handler = ResponseHandler
        self.response_handler = response_handler

    # === Story services ===
    # --- Client ---

    def get_story_update(self,
                         user_id: Uid = None,
                         story_id = None,
                         entry: int = -1,
                         section: str | int = None) -> JournalEntry:
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = False) as story:
            res = StoryHandler.get_update(story, entry, section)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    def do_story_action(self,
                        user_id: Uid = None,
                        story_id = None,
                        action_id: Uid = None,
                        payload: dict = None) -> JournalEntry:
        payload = payload or {}
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = True) as story:
            StoryHandler.do_action(story, action=action_id, **payload)
            res = StoryHandler.get_update(story)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    def get_story_status(self,
                         user_id: Uid = None,
                         story_id=None) -> StoryStatus:
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = False) as story:
            res = StoryHandler.get_status(story)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    # --- Dev ---

    def inspect_node(self,
                     user_id: Uid = None,
                     story_id=None,
                     node_id: Uid = None) -> NodeInfo:
        if not node_id:
            raise ValueError("Inspect requires a node_id parameter")
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = False) as story:

            return StoryHandler.inspect_node(story, node_id)

    def goto_node(self,
                  user_id: Uid = None,
                  story_id=None,
                  node_id: Uid = None) -> JournalEntry:
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = True) as story:
            StoryHandler.goto_node(story, node_id)
            res = StoryHandler.get_update(story)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    def check_expr(self,
                   user_id: Uid = None,
                   story_id = None,
                   condition: str = "") -> RuntimeInfo:
        if not condition:
            raise TypeError("Check requires a condition parameter")
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = False) as story:
            res = StoryHandler.check_expr(story, condition)
            return RuntimeInfo(expr=condition, result=res)

    def apply_effect(self,
                     user_id: Uid = None,
                     story_id=None,
                     effect: str = None) -> RuntimeInfo:
        if not effect:
            raise TypeError("Apply requires a effect parameter")
        with self.persistence_manager.open_story(user_id = user_id,
                                                 story_id = story_id,
                                                 write_back = True) as story:
            StoryHandler.apply_effect(story, effect)
            return RuntimeInfo(expr=effect, result='apply ok')

    # === User services ===
    # --- Public ---

    def create_user(self, secret: str = None) -> UserSecret:
        user = UserHandler.create_user(secret=secret)
        self.persistence_manager.save(user)
        return UserSecret( user.uid, user.secret )

    @staticmethod
    def key_for_secret(secret: str = None) -> UserSecret:
        user_id, user_secret = UserHandler.get_key_for_secret(secret=secret)
        return UserSecret( user_id, user_secret )

    # --- Client ---

    def update_user_secret(self, user_id, secret) -> UserSecret:
        user = self.persistence_manager.load(user_id)
        user.secret = secret
        self.persistence_manager.save(user)       # add at new loc
        self.persistence_manager.remove(user_id)  # remove at old loc
        return UserSecret( user.uid, user.secret )

    def get_user_info(self, user_id: Uid) -> UserInfo:
        with self.persistence_manager.open(user_id) as user:
            res = UserHandler.get_user_info(user)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    def remove_user(self, user_id: Uid):
        with self.persistence_manager.open(user_id) as user:  # type: User
            story_ids = user.world_for_story.values()
        for uid in [ *story_ids, user_id ]:
            self.persistence_manager.remove(uid)
        return {'remove_user': user_id,
                'result': f'remove user {user_id} and stories {story_ids} ok'}

    def remove_story(self, user_id: Uid, world_id: UniqueLabel) -> dict:
        with self.persistence_manager.open(user_id, write_back=True) as user:
            story_id = UserHandler.remove_story(user, world_id)
            self.persistence_manager.remove(story_id)
            return {'remove_story': world_id, 'result': f"remove {story_id} ok"}

    def set_current_story_id(self, user_id: Uid, world_id: UniqueLabel):
        with self.persistence_manager.open(user_id, write_back=True) as user:
            UserHandler.set_current_story(user, world_id)
            # return an update?

    def create_story(self, user_id: Uid, world_id: UniqueLabel) -> JournalEntry:
        with self.persistence_manager.open(user_id, write_back=True) as user:
            # this associates the user automatically
            story = WorldHandler.create_story( world_id, user=user )
            UserHandler.add_story(user, story)
            UserHandler.set_current_story(user, story)
            res = StoryHandler.get_update(story)
            # disassociate the user
            story.user = None
            self.persistence_manager.save(story)

            if self.response_handler:
                res = self.response_handler.format_response(res)
            return res

    # === World services ===
    # --- Public ---

    def get_world_info(self, world_id: UniqueLabel) -> WorldInfo:
        res = WorldHandler.get_world_info(world_id)

        if self.response_handler:
            res = self.response_handler.format_response(res)
        return res

    def get_world_list(self) -> WorldList:
        res = WorldHandler.get_world_list()

        if self.response_handler:
            res = self.response_handler.format_response(res)
        return res

    # --- Dev ---

    def get_scene_list(self, world_id: UniqueLabel) -> WorldSceneList:
        res = WorldHandler.get_scene_list(world_id)

        if self.response_handler:
            res = self.response_handler.format_response(res)
        return res

    # === System services ===
    # --- Public ---

    def get_system_info(self) -> SystemInfo:
        res = SystemHandler.get_system_info()

        if self.response_handler:
            res = self.response_handler.format_response(res)
        return res

    # --- Dev ---

    @staticmethod
    def reset_system(hard=False):
        SystemHandler.reset_system(hard=hard)
