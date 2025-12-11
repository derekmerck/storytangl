from __future__ import annotations
from typing import ClassVar, TYPE_CHECKING, Optional
import copy
import logging

from tangl.entity import SingletonEntity
from tangl.graph import GraphFactory
from tangl.entity.mixins import HasNamespace, NamespaceHandler, TemplateHandler
# from tangl.entity.mixins.templated import TemplateRegistry, TemplateKey
from tangl.graph.mixins import HasPluginManager, WrappedSingleton, PluginHandler
from tangl.user import User
from tangl.story.story import Story
from tangl.story.scene import Scene
from tangl.story.actor import Actor
from tangl.story.place import Place
from tangl.story.asset import AssetType
from tangl.story.player import Player
from tangl.script import ScriptManager
from tangl.resource_registry.resource_registry import HasResourceRegistry

# todo: was trying to avoid using tangl.media directly here
from tangl.media.svgforge import SvgForge

logger = logging.getLogger("tangl.world")

class World(SingletonEntity,
            HasPluginManager,
            HasResourceRegistry,
            # HasTemplateRegistry,
            HasNamespace,
            GraphFactory,
            arbitrary_types_allowed=True, frozen=False):
    """
    World is a GraphFactory for Stories and StoryNodes.

    It also collects several registries and managers into a single point of access for story logic.

    - script manager (for managing the story recipe)
    - plugin manager (for injecting world-specific behaviors and classes)
    - media resources (for managing story media like images or audio)
    - template registry (for dynamically created nodes like NPCs)
    - asset registry (for static 'nouns' that can share a reference between story instances, like a sword)
    """

    _instances: ClassVar[dict[str, World]]

    # plugin_manager: PluginManager = None        # inherited from HasPluginManager
    # media_resources: ResourceDomain = None      # inherited from HasResourceRegistry
    # template_registry: TemplateRegistry = None  # inherited from HasTemplateRegistry
    script_manager: ScriptManager = None
    asset_registry: dict = None                 # for ns
    scene_art_forge: Optional[SvgForge] = None

    @property
    def script(self):
        # convenience accessor
        return self.script_manager

    # --------------

    def create_graph(self,
                     user: User = None,
                     **kwargs) -> Story:
        """Returns an _un-entered_ story object"""
        graph_data ={
            'locals': copy.deepcopy(self.script.globals() or {}),
            'user': user,
            **kwargs
        }
        story = super().create_graph(base_cls=Story, defer_init=True, **graph_data)
        player = self.create_node(base_cls=Player, graph=story)
        story.add_node(player)

        for scene in self.script.scenes_data():
            self.create_node(base_cls=Scene, graph=story, **scene)

        for actor in self.script.actors_data():
            self.create_node(base_cls=Actor, graph=story, **actor)

        for place in self.script.places_data():
            self.create_node(base_cls=Place, graph=story, **place)

        # for k, sc in self.script.assets.items(): ...

        # invoke deferred initialization hook
        PluginHandler.on_init_entity(self.pm, story)

        # enter the story
        story.enter()

        return story

    # --------------

    # todo: want to provide handles to assets in ns
    # @NamespaceHandler.strategy
    # def _include_assets_in_ns(self) -> Mapping:
    #     maps = [ self.asset_manager.get_assets() ]
    #     return ChainMap(*maps)

    @NamespaceHandler.strategy
    def _include_progression_names(self):
        logger.debug("including progression names in ns")
        # if the world uses a progress system, the measures should be injected here
        from tangl.mechanics.progression.measures import measure_namespace
        return {"Q": measure_namespace}

    # ---------------

    # convenience functions delegated to script manager for the world handler

    def get_scenes(self) -> list[dict]:
        # returns a list of scene script dumps
        return self.script.scenes_data()

    def get_info(self) -> dict:
        res = self.script.metadata().model_dump()
        res['label'] = self.label
        return res
