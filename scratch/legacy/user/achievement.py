from __future__ import annotations
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel
from tangl.core import Singleton, Entity
from tangl.core.graph import Token

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


class UserWorldMetadata(Entity):
    # Aggregate info from all stories in a given world

    world_id: WorldId = Field(..., alias='world')
    num_stories: int = 0
    num_stories_completed: int = 0
    total_turns: int = 0
    first_start_time: datetime = None
    last_interaction_time: datetime = None
    achievements: list[UserAchievementRecord] = Field(default_factory=list)

    @classmethod
    def from_story_metadata(cls, *story_metadata: UserStoryMetadata) -> Self:
        return cls(
            num_stories=len(story_metadata),
            num_stories_completed=sum([1 for x in story_metadata if x.completed]),
            total_turns = sum([x.current_turn for x in story_metadata]),
            first_start_time = min([x.start_time for x in story_metadata]),
            last_interaction_time = max([x.last_interaction_time for x in story_metadata]),
            achievements = set([a for x in story_metadata for a in x.achievements])
        )

    @on_gather_context.register()
    def _provide_achievements(self):
        return {'achievements': { self.world_id: self.achievements}}

class UserStoryMetadata(HasContext):
    world_id: WorldId
    story_id: StoryId
    engine_version: str = None
    world_version: str = None
    current_turn: int = 0
    # achievements: list[UserAchievementRecord] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    completion_time: datetime = None
    last_interaction_time: datetime = Field(default_factory=datetime.now)

    @property
    def completed(self) -> bool:
        return self.completion_time is not None

    @property
    def mark_as_completed(self):
        self.completion_time = datetime.now()
        self.last_interaction_time = datetime.now()

    def increment_turn(self) -> None:
        self.current_turn += 1
        self.last_interaction_time = datetime.now()

    def add_achievement(self, *, achievement_id, **kwargs) -> None:
        self.achievements.append(
            UserAchievementRecord(
                world_id=self.world_id,
                achievement_id=achievement_id,
                **kwargs
            )
        )
        self.last_interaction_time = datetime.now()

    @on_gather_context.register()
    def _provide_hooks(self, **context) -> StringMap:
        return {'add_achievement': self.add_achievement,
                'increment_turn': self.increment_turn,
                'mark_as_completed': self.mark_completed}
