from __future__ import annotations
from typing import Self, Mapping
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, StringMap, Hash
from tangl.utils.hash_secret import hash_for_secret
from tangl.business.core import Entity
from tangl.business.core.handlers import on_gather_context, HasContext
from .achievement import UserAchievementRecord

StoryId = UUID
WorldId = UniqueLabel


class UserWorldMetadata(HasContext):
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
    achievements: list[UserAchievementRecord] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    completion_time: datetime = None
    last_interaction_time: datetime = Field(default_factory=datetime.now)

    @property
    def completed(self) -> bool:
        return self.completion_time is not None

    def add_achievement(self, *, achievement_id, **kwargs) -> None:
        self.achievements.append(
            UserAchievementRecord(
                world_id=self.world_id,
                achievement_id=achievement_id,
                **kwargs
            )
        )

    @on_gather_context.register()
    def _provide_achievement_hook(self, **context) -> StringMap:
        return {'add_achievement': self.add_achievement}

class User(HasContext):
    """
    User accounts do not link their stories, they only carry references
    to story id's, which are managed separately.
    """

    def set_secret(self, s: str):
        # Note, secret is not preserved, only its hash digest is
        # tracked with the content_hash attribute.  Users are
        # automatically discoverable by their secret hash alias.
        self.content_hash = hash_for_secret(s)

    current_story_id: StoryId = None
    story_metadata: list[UserStoryMetadata] = None

    def current_story_metadata(self) -> UserStoryMetadata:
        return UserStoryMetadata.filter_by_criteria(
            self.story_metadata,
            story_id=self.current_story_id,
            return_first=True)

    @on_gather_context.register()
    def _provide_current_story_metadata(self, **context) -> StringMap:
        return self.current_story_metadata().gather_context()

    def worlds_metadata(self) -> list[UserWorldMetadata]:
        worlds_played = { s.world_id for s in self.story_metadata }
        res = []
        for world_id in worlds_played:
            world_stories = UserStoryMetadata.filter_by_criteria(world_id=world_id)
            if world_stories:
                res.append(UserWorldMetadata.from_story_metadata())
        return res

    @on_gather_context.register()
    def _provide_worlds_metadata(self, **context) -> StringMap:
        return { v.world_id: v.gather_context() for k, v in self.worlds_metadata() }


class HasUser(Entity):
    user: User = None

    @on_gather_context.register()
    def _provide_user_context(self, **context):
        if self.user is not None:
            return self.user.gather_context()
