from uuid import UUID

from tangl.type_hints import UniqueLabel
from tangl.core import Entity

WorldId = UniqueLabel

class User(Entity):

    secret: str = None
    api_key: str = None

    current_story_id: UUID = None
    story_metadata: dict[UUID, dict] = None
    world_achievements: dict[UniqueLabel, dict] = None  # By world
