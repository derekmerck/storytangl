from pydantic import BaseModel

from tangl.core import Singleton, Entity
from tangl.core import on_gather_context, HasContext

from pydantic import ConfigDict

# from tangl.scripting import ScriptManager
# from tangl.media.media_registry import MediaRegistry
# from tangl.core.handler import StrategyRegistry
AssetRegistry = StrategyRegistry = MediaRegistry = ScriptManager = dict

class World(HasContext, Singleton):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    script_manager: ScriptManager = None
    media_registry: MediaRegistry = None
    hook_registry: StrategyRegistry = None
    asset_registry: AssetRegistry = None


class HasWorld(Entity):
    world: World = None

    @on_gather_context.register()
    def _provide_world_context(self, **context):
        if self.world is not None:
            return self.world.gather_context()
