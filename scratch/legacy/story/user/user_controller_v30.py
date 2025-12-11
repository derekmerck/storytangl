
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID
import logging
import string
import random

from tangl.core.handler import BaseHandler
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import uuid_for_secret
from tangl.utils.get_code_name import get_code_name
from .user import User
from .user_info_model import UserSecret, UserInfo

if TYPE_CHECKING:
    from tangl.story import Story
    from tangl.story.world import World
    Storylike = Story | World | UUID | UniqueLabel
else:
    Story = World = StoryLike = object

logger = logging.getLogger(__name__)

def random_string(length=10):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class UserHandler(BaseHandler):
    """
    Provides standard methods for interacting with a user object.

    public api:
      - create_user
      - get_key_for_secret

    client api:
      - get_user_info
      - update_user_secret
      - set_current_story
      - add_story
      - remove_story

    dev api:
      - get_user_list

    backend api:
      - register_code_names

    supports hooks:
      - on_create_user
    """

    ###########################################################################
    # User Public API
    ###########################################################################

    @classmethod
    def create_user(cls, secret=None, **kwargs) -> User:
        secret = secret or cls._get_random_code_name()
        return User(secret=secret, **kwargs)

    @classmethod
    def get_key_for_secret(cls, secret: str = None) -> UserSecret:
        secret = secret or cls._get_random_code_name()
        key = uuid_for_secret(secret)
        return UserSecret(key, secret)

    ###########################################################################
    # User Client API
    ###########################################################################

    @classmethod
    def get_user_info(cls, user: User) -> UserInfo:
        return UserInfo(
            user_id=user.uid,
            user_secret=user.secret,
            created_dt=user.created_dt,
            # last_played_dt=user.last_played_dt,
            worlds_played=list(user.world_metadata.keys()),
            # stories_finished=0,
            # todo: this is not quite right -- only the completed stories represented...
            turns_played=sum( [ x.get('turns', 0) for x in user.world_metadata.values() ] ),
            achievements=None
        )

    @classmethod
    def update_user_secret(cls, user: User, secret: str = None) -> UserSecret:
        user.secret = secret or cls._get_random_code_name()
        return UserSecret(user.uid, user.secret)

    # Story bookkeeping

    @classmethod
    def _normalize_story_id(cls, user: User, story: 'Storylike') -> tuple[UUID, UniqueLabel]:
        """Normalize ( user, obj/id ) to ( story_id, world_id )"""

        if story is None:
            raise ValueError("`_normalize_story_id` called improperly, story is None")

        from tangl.story import Story
        from tangl.story.world import World

        if isinstance(story, Story):
            # It's a story
            story_id = story.uid
            world_id = story.world.label
        elif isinstance(story, UUID):
            # It's a story_id
            story_id = story
            world_id = user.world_by_story.get( story_id )
        elif isinstance(story, World):
            # It's a world
            world_id = story.world.label
            story_id = user.story_by_world.get( world_id )
        elif isinstance(story, UniqueLabel):
            # It's a world_id
            world_id = story
            story_id = user.story_by_world.get( world_id )
        else:
            raise TypeError(f"Cannot infer story/world id's for {user} from {story}")

        logger.debug(f"For {user!r} with {story!r}, found story {story_id}, world {world_id}")

        return story_id, world_id

    @classmethod
    def add_story(cls, user, story: 'Story'):
        user.world_for_story[story.uid] = story.world.label
        user.world_metadata[story.world.label] = dict()

    @classmethod
    def remove_story(cls, user: User, story: 'Storylike') -> UUID:
        """Returns uid of the removed story"""
        story_id, world_id = cls._normalize_story_id(user, story)
        del user.world_for_story[story_id]
        if user.current_story_id == story_id:
            user.current_story_id = None
        return story_id

    @classmethod
    def set_current_story(cls, user: User, story: 'Storylike'):
        if story is None:
            user.current_story_id = None
        else:
            user.current_story_id, _ = cls._normalize_story_id(user, story)

    ###########################################################################
    # Backend API
    ###########################################################################

    # "on_init_world" can register default code names with the UserHandler class

    _code_name_adj: ClassVar[list[str]] = list()
    _code_name_nouns: ClassVar[list[str]] = list()

    @classmethod
    def _get_random_code_name(cls):
        try:
            return get_code_name(cls._code_name_adj, cls._code_name_nouns)
        except NameError:
            return random_string()

    @classmethod
    def register_code_names(cls, adj: [list[str]] = None, nouns: list[str] = None):
        if adj:
            cls._code_name_adj.extend(adj)
        if nouns:
            cls._code_name_nouns.extend(nouns)
