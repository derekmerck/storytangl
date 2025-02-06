from uuid import UUID

from tangl.type_hints import UniqueLabel
from tangl.core.entity import Entity

WorldId = UniqueLabel

class User(Entity):

    def set_secret(self, s: str):
        self.data = hash_secret(s)

    current_story_id: UUID = None
    story_metadata: dict[UUID, dict] = None
    world_achievements: dict[UniqueLabel, dict] = None  # By world
