from __future__ import annotations
from typing import Literal, Protocol, Callable, Any, TypeVar
import contextlib
from datetime import datetime

from pydantic import BaseModel

from .type_hints import StringMap, Identifier, UniqueString
from .entity import TaskHandler, TextFragment
from .system import SystemHandler
from .persistence import PersistenceManager

from .journal import JournalEntry
from .content import MediaData
from .user import UserId, UserSecret, UserInfo, UserManager, UserFeature
from .world import WorldId, WorldInfo, WorldFeature
from .story import StoryId, StoryInfo, StoryManager, StoryFeature
from .story_nodes import StoryNodeInfo
from .content import MediaFragment, RIT

# ----------------
# API Function Annotations
# ----------------
def req_write_back(func: Callable) -> Callable:
    """Annotate func access as read-write"""

def privileged(func: Callable) -> Callable:
    """Annotate func access as privileged"""

# ----------------
# Service Handlers
# ----------------
class HasPersistenceManager(Protocol):
    persistence_manager: PersistenceManager

    @contextlib.contextmanager
    def _open_story(self, story_id: StoryId, write_back: bool = False) -> StoryManager: ...

    @contextlib.contextmanager
    def _open_user(self, user_id: UserId, write_back: bool = False) -> UserManager: ...

    @contextlib.contextmanager
    def _open_story_for_user(self, user_id: UserId, write_back: bool = False) -> StoryManager: ...


class WorldServiceHandler(HasPersistenceManager):

    @req_write_back
    async def create_story(self,
                           user_id: UserId,
                           world_id: WorldId,
                           story_config: StringMap = None
                           ) -> RuntimeInfo:
        """Start new story instance"""

    @classmethod
    # world controller
    async def get_world_info(cls,
                             world_id: WorldId,
                             feature_config: dict[WorldFeature, Any] = None
                             ) -> WorldInfo: ...

    @classmethod
    async def get_world_media(cls, media_id: Identifier) -> MediaData: ...  # or offload to media server


class StoryServiceHandler(HasPersistenceManager):

    async def get_story_info(self,
                             user_id: UserId,
                             feature_config: dict[StoryFeature, Any] = None
                             ) -> StoryInfo:
        """Get current story state by features, including bookmarks"""

    async def get_story_journal_entry(self,
                                      user_id: UserId,
                                      which: str | int
                                      ) -> JournalEntry:
        """Get story journal entry - text, choices, media - latest or specific historical entry"""

    async def get_story_media(self,
                              user_id: UserId,
                              media_id: Identifier
                              ) -> MediaData: ...  # or redirect to media server

    @req_write_back
    async def do_action(self,
                        user_id: UserId,
                        action_id: Identifier,
                        action_payload: StringMap = None
                        ) -> JournalEntry:
        """Execute a story action and return resulting update"""

    # history
    @req_write_back
    async def create_bookmark(self,
                              user_id: UserId,
                              bookmark_metadata: StringMap = None
                              ) -> RuntimeInfo:
        """Create manual save point"""

    @req_write_back
    async def restore_bookmark(self,
                               user_id: UserId,
                               bookmark_id: Identifier) -> RuntimeInfo:
        ...

    @req_write_back
    async def delete_bookmark(self,
                              user_id: UserId,
                              bookmark_id: Identifier) -> RuntimeInfo:
        """Remove a saved state"""

    # debug
    @privileged
    def get_node_info(self, user_id: UserId, node_id: Identifier) -> StoryNodeInfo: ...
    @privileged
    def do_check_expr(self, user_id: UserId, expr: str) -> RuntimeInfo: ...
    @privileged
    @req_write_back
    def do_apply_expr(self, user_id: UserId, expr: str) -> RuntimeInfo: ...
    @privileged
    @req_write_back
    def do_goto_node(self, user_id: UserId, node_id: Identifier) -> RuntimeInfo: ...

class UserServiceHandler(HasPersistenceManager):
    # account controller

    @req_write_back
    async def create_user(self, secret: str = None) -> UserSecret:
        """Create new user, optionally with specific secret"""

    async def get_user_info(self,
                            user_id: UserId,
                            feature_config: dict[UserFeature, Any] = None
                            ) -> UserInfo:
        """Get current user information, prefs, current story, active stories/worlds"""

    @req_write_back
    async def update_user_current_story(self, user_id: UserId, new_story_id: StoryId) -> RuntimeInfo:
        """Update user current story"""

    @req_write_back
    async def update_user_secret(self, user_id: UserId, new_secret: str) -> UserSecret:
        """Change user secret, invalidating old api_key"""

    @req_write_back
    async def update_user_prefs(self, user_id: UserId, prefs_config: dict[UserFeature, Any] = None) -> RuntimeInfo:
        """Update user preferences"""

    @req_write_back
    async def delete_user(self, user_id: UserId) -> RuntimeInfo: ...


# -----------------
# Service
# -----------------
class UnifiedServiceManager(SystemHandler,
                            WorldServiceHandler,
                            StoryServiceHandler,
                            UserServiceHandler):
    ...
# Otherwise can pass a shared persistence manager to service handlers

ClientFeature = UniqueString
# HTML text, include media / media format preference

RV = TypeVar('RV')

class ResponseHandler(TaskHandler):

    @classmethod
    def handle_text_content(cls, data: TextFragment) -> TextFragment:
        ...

    @classmethod
    def handle_media_content(cls, data: RIT) -> MediaFragment:
        ...

    @classmethod
    def handle_response(cls, response: BaseModel, client_config: dict[ClientFeature, Any] = None):
        ...


# ----------------
# Runtime Info
# ----------------
class RuntimeInfo(BaseModel):
    timestamp: datetime
    task_type: Literal['create', 'read', 'update', 'delete', 'reset']
    object_type: Literal['system', 'world', 'story', 'node']
    object_id: Identifier
    task: str
    result: Any
