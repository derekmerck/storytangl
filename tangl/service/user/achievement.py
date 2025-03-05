from __future__ import annotations
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel

StoryId = UUID
WorldId = UniqueLabel
AchievementId = UniqueLabel

class UserAchievementRecord(BaseModel):
    world_id: WorldId = Field(..., alias='world')
    achievement_id: AchievementId = Field(..., alias='achievement')
    timestamp: datetime = Field(default_factory=datetime.now)
