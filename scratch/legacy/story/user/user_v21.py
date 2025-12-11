from __future__ import annotations
from uuid import UUID
from typing import Optional
from datetime import datetime

from pydantic import Field, field_serializer, field_validator

from tangl.type_hints import Uid, UniqueLabel
from tangl.entity import Entity
from tangl.entity.mixins import HasNamespace, NamespaceHandler
from tangl.utils.uuid_for_secret import uuid_for_secret


class User(HasNamespace, Entity):
    """
    User's uid is based on encoding their hopefully-unique "secret" string
    User does not keep _any_ direct links to stories.

    User organizes stories and user contexts across all games, providing a single
    point of access for the namespace in any story to reference metadata about
    achievements in other games as well.
    """

    uid_: Optional[UUID] = None

    # required, the user handler will generate one if necessary
    secret: str

    @property
    def uid(self) -> UUID:
        return uuid_for_secret(self.secret)

    current_story_id: Optional[Uid] = None

    world_for_story: dict[Uid, UniqueLabel] = Field(default_factory=dict)
    @property
    def story_for_world(self) -> dict[UniqueLabel, Uid]:
        # This is degenerate, only includes the _latest_ story for each world
        return { v: k for k, v in self.world_for_story.items()}

    world_metadata: dict[UniqueLabel, dict] = Field(default_factory=dict)
    # keep this with user, so it's available in all stories, regardless of
    # whether that story is active

    @NamespaceHandler.strategy
    def _include_world_metadata(self):
        return self.world_metadata

    class PooledAchievements(set):

        def __init__(self, user: User):
            super().__init__()
            self.user = user
            for w, meta in self.user.world_metadata.items():
                w_achievements = meta.get('achievements')
                if w_achievements:
                    self.update(w_achievements)

        def add(self, value: str):
            world_id = self.user.world_for_story[self.user.current_story_id]
            w_meta = self.user.world_metadata[world_id]
            if 'achievements' not in w_meta:
                w_meta['achievements'] = set()
            w_meta['achievements'].add(value)

    def achievements(self) -> set[str]:
        return User.PooledAchievements(self)

    # def model_dump(self, *args, **kwargs):
    #     res = super().model_dump(*args, **kwargs)
    #     res |= {'uid': self.uid,
    #             'created_dt': self.created_dt.isoformat(),
    #             # 'last_played_dt': self.last_played_dt.isoformat()
    #             }
    #     return res

    created_dt: datetime = Field(default_factory=datetime.now)
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

    @property
    def turns_played(self):
        # increment `player.metadata[world_id].turns_played` when step_count is increased
        return sum( [ meta.get('turns_played', 0) for meta in self.world_metadata.values() ] )
