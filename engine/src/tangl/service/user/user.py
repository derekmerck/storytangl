from __future__ import annotations

from types import NotImplementedType
from typing import Self, Mapping, TYPE_CHECKING, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, field_serializer

from tangl.type_hints import UniqueLabel, StringMap, Hash
from tangl.utils.hash_secret import hash_for_secret
from tangl.core.entity import Entity
# from tangl.core.services import on_gather_context, HasContext
# from .achievement import UserAchievementRecord

# if TYPE_CHECKING:
#     from tangl.story.story import Story

StoryId = UUID
WorldId = UniqueLabel


class User(Entity):
    """
    User organizes stories and user contexts across all games, providing a single
    point of access for the namespace in any story to reference metadata about
    achievements in other games as well.

    User accounts do not directly link their stories, they only carry
    references to story id's, which are managed separately.
    """

    content_hash: Hash = Field(None, json_schema_extra={'is_identifier': True})

    def set_secret(self, s: str):
        """
        A user secret will be automatically generated and returned by the user
        handler at creation if one is not provided.

        Note that the secret is not preserved, only its hash digest is tracked
        as the content_hash attribute.

        Users are automatically discoverable at the service layer by their secret
        hash alias.
        """
        self.content_hash = hash_for_secret(s)

    created_dt: datetime = Field(default_factory=datetime.now, init=False)
    # update this field on access
    last_played_dt: Optional[datetime] = None

    @field_validator('created_dt', 'last_played_dt', mode='before')
    @classmethod
    def _from_isoformat(cls, data):
        if isinstance(data, str):
            return datetime.fromisoformat(data)
        return data

    @field_serializer('created_dt', 'last_played_dt')
    def _to_isoformat(self, data):
        if data:
            return data.isoformat()

    privileged: bool = False  # User is authorized to use dev controllers

    current_ledger_id: UUID | None = None

    # @property
    # def current_story(self):
    #     # This is _only_ used for setting
    #     raise NotImplementedError
    #
    # @current_story.setter
    # def current_story(self, story: Story):
    #     self.current_story_id = story.uid
    #     if getattr(story, "world"):
    #         self.world_by_story[story.uid] = story.world.label

    # all_story_metadata: dict[StoryId, UserStoryMetadata] = None
    #
    # def current_story_metadata(self) -> UserStoryMetadata:
    #     return self.all_story_metadata[self.current_story_id]
    #
    # @on_gather_context.register()
    # def _provide_current_story_metadata(self, **context) -> StringMap:
    #     return self.all_story_metadata[self.current_story_id].gather_context()
    #
    # def worlds_metadata(self) -> list[UserWorldMetadata]:
    #     worlds_played = { s.world_id for s in self.story_metadata }
    #     res = []
    #     for world_id in worlds_played:
    #         world_stories = UserStoryMetadata.filter_by_criteria(world_id=world_id)
    #         if world_stories:
    #             res.append(UserWorldMetadata.from_story_metadata())
    #     return res
    #
    # @on_gather_context.register()
    # def _provide_worlds_metadata(self, **context) -> StringMap:
    #     return { k: v.gather_context() for k, v in self.worlds_metadata() }
    #
    # @on_gather_context.register()
    # def _include_achievements(self):
    #     raise NotImplementedError

    ################

    # world_by_story: dict[UUID, UniqueLabel] = Field(default_factory=dict)
    #
    # @property
    # def story_by_world(self) -> dict[UniqueLabel, UUID]:
    #     # This is degenerate, only includes the _latest_ story for each world
    #     return {v: k for k, v in self.world_by_story.items()}
    #
    # world_metadata: dict[UniqueLabel, StringMap] = Field(default_factory=dict)

    # class PooledAchievements(set):
    #
    #     def __init__(self, user: User):
    #         super().__init__()
    #         self.user = user
    #         for w, meta in self.user.world_metadata.items():
    #             w_achievements = meta.get('achievements')
    #             if w_achievements:
    #                 self.update(w_achievements)
    #
    #     def add(self, value: str):
    #         world_id = self.user.world_for_story[self.user.current_story_id]
    #         w_meta = self.user.world_metadata[world_id]
    #         if 'achievements' not in w_meta:
    #             w_meta['achievements'] = set()
    #         w_meta['achievements'].add(value)


# class HasUser(Entity):
#     user: User = None
#
#     @on_gather_context.register()
#     def _provide_user_context(self, **context):
#         if self.user is not None:
#             return self.user.gather_context()
