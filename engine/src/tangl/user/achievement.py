from __future__ import annotations
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel
from tangl.core.entity import Singleton
from tangl.core.graph import SingletonNode

StoryId = UUID
WorldId = UniqueLabel
AchievementId = UniqueLabel

class UserAchievement(Singleton):
    world_id: WorldId
    achievement_id: AchievementId

class UserAchievementRecord(BaseModel):
    world_id: WorldId = Field(..., alias='world')
    achievement_id: AchievementId = Field(..., alias='achievement')
    timestamp: datetime = Field(default_factory=datetime.now)
