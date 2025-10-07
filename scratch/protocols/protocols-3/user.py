from __future__ import annotations
from typing import TYPE_CHECKING, Iterable, Protocol, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .type_hints import UniqueString, Identifier
from .entity import Entity, Registry, TaskHandler

if TYPE_CHECKING:
    from .story import Story, StoryId, StoryInfo, StoryAchievementInfo

# ----------------
# User-Account-related Type Hints
# ----------------
UserId = UUID
UserFeature = UniqueString  # achievements, privilege levels, content-warnings, prefs


# ----------------
# User Account Model
# ----------------
class User(Entity):
    uid: UserId
    auth: Any
    current_story_id: Identifier
    all_stories: Registry[StoryInfo]
    # todo: achievements are kept with the story, but need to be available on the user for other stories?
    user_prefs: dict[UserFeature, Any]


# ----------------
# User Account Manager
# ----------------
class UserManager(TaskHandler):
    """Active user session management"""

    user: User

    @property
    def all_achievements(self) -> Iterable[StoryAchievementInfo]:
        ...

    @property
    def total_turns(self) -> Iterable[StoryAchievementInfo]:
        ...

    @classmethod
    def create_user(cls, secret: str = None) -> User:
        """Create new user, optionally with specific secret"""

    def get_info(self) -> UserInfo:
        """Get current user information, prefs, current story, active stories/worlds"""

    def update_current_story(self, new_story: Story):
        """Update user current story"""

    def update_secret(self, new_secret: str):
        """Change user secret"""

    def update_prefs(self, prefs_config: dict[UserFeature, Any] = None):
        """Update user preferences"""


# ----------------
# User Account Info
# ----------------
class UserInfo(BaseModel, allow_extra=True):
    user_id: UserId
    created: datetime
    last_modified: datetime
    current_story_id: StoryId
    user_prefs: dict[UserFeature, Any]
    all_stories: list[StoryInfo]  # simplified summary with bookmarks
    all_total_turns: int
    all_achievements: list[StoryAchievementInfo]

class UserSecret(BaseModel):
    """User authentication details"""
    user_id: UserId
    secret: str   # User's secret for recovery
    api_key: str  # Hashed authentication token

