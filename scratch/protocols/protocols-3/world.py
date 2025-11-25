from __future__ import annotations
from typing import Union, Protocol, TYPE_CHECKING

from pydantic import BaseModel

from tangl.type_hints import Identifier, UniqueLabel, StringMap
from .entity import TaskHandler, Registry, Singleton, Renderable, HasConditions
from .graph import NodeTemplate

if TYPE_CHECKING:
    from .content import HasMedia, MediaFragment
    from .story import Story, StoryFeature
    from .story_nodes import AssetType
    from .user import User

# ----------------
# Story-World-related Type Hints
# ----------------
WorldId = Identifier
WorldFeature = UniqueLabel    # ui branding, media, supports history
AchievementId = Identifier

# ----------------
# Story-World Model
# ----------------
class World(Singleton):
    uid: WorldId
    story_metadata: StringMap
    story_handlers: Registry[TaskHandler]
    story_assets: Registry[AssetType]
    story_script: Registry[NodeTemplate]
    story_achievements: Registry[AchievementType]

class AchievementType(Renderable, HasConditions, HasMedia, Singleton):
    uid: AchievementId


# ----------------
# Story-World Manager
# ----------------
class WorldManager(Protocol):
    """Story-world management, no story instance or user"""

    world: World

    async def get_info(self) -> WorldInfo:
        """
        Get detailed world information including available ui branding, features,
        chapters, requirements, content warnings, story features etc.
        """

    async def create_story(self,
                           user: User,
                           story_config: StringMap = None
                           ) -> Story:
        """Start new story instance"""

# ----------------
# Story-World Info
# ----------------
class WorldInfo(BaseModel, allow_extra=True):
    world_id: WorldId
    title: str
    author: str
    version: str
    summary: str
    story_achievements: set[AchievementInfo]
    world_features: set[WorldFeature]     # features supported by world manager, branding, etc.
    story_features: set[StoryFeature]     # features supported by story manager, maps, inv, history, etc.
    media: list[MediaFragment] = None

class AchievementInfo(BaseModel):
    achievement_id: AchievementId
    label: Union[str, None] = None
    text: str = None
    icon: str = None
    media: list[MediaFragment] = None
