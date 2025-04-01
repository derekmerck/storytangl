from pydantic import BaseModel

from tangl.core import Singleton, Entity
from tangl.core.handlers import on_gather_context, HasContext


class World(HasContext, Singleton):
    ...

class HasWorld(Entity):
    world: World = None

    @on_gather_context.register()
    def _provide_world_context(self, **context):
        if self.world is not None:
            return self.world.gather_context()
