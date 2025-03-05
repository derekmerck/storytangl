from pydantic import BaseModel

from tangl.business.core import Singleton, Entity
from tangl.business.core.handlers import on_gather_context
from tangl.business.story.story_node import StoryNode

class WorldInfo(BaseModel):
    world_id: str
    # etc.

class World(StoryNode, Singleton):
    ...

class HasWorld(Entity):
    world: World = None

    @on_gather_context.register()
    def _provide_world_context(self, **context):
        if self.world is not None:
            return self.world.gather_context()
