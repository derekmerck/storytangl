import logging

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler
from tangl.core.entity.handlers import SelfFactoringHandler
from tangl.story import Story
from tangl.story.scene import Scene
from tangl.story.actor import Actor
from .world import World
from .world_info_models import WorldInfo, WorldListItem, WorldList, WorldSceneList, WorldSceneItem

Worldlike = World | UniqueLabel

# MediaRef = str

logger = logging.getLogger(__name__)

class WorldHandler(BaseHandler):
    """
    Provides basic methods for interacting with World singleton objects.

    public api:
      - get_world_list
      - get_world_info

    client api:
      - create_story(user)

    dev api:
      - get_scene_list

    supports hooks:
      - on_create_story
    """

    @staticmethod
    def _normalize_world_arg(world_or_world_id: Worldlike) -> World:
        if isinstance(world_or_world_id, UniqueLabel):
            return World.get_instance(world_or_world_id)
        elif isinstance(world_or_world_id, World):
            return world_or_world_id
        raise TypeError(f"Wrong type for {world_or_world_id} ({type(world_or_world_id)})")

    ###########################################################################
    # World Public API
    ###########################################################################

    @classmethod
    def get_world_info(cls, world: World) -> WorldInfo:
        world = cls._normalize_world_arg(world)
        res = world.script_manager.get_story_metadata()
        res['label'] = world.label
        res = WorldInfo(**res)
        return res

    @classmethod
    def get_world_list(cls) -> WorldList:
        worlds = World._instances.values()  # type: list[World]
        infos = [ cls.get_world_info(w) for w in worlds ]
        logger.debug(infos)
        items = []
        for info in infos:
            data = {'key': info.label, 'value': info.title}
            if x := info.ui_config.brand_color:
                data['style_dict'] = {'color': x}
            items.append( data )
        res = [ WorldListItem(**v) for v in items ]
        return res


    ###########################################################################
    # World Client API
    ###########################################################################

    @classmethod
    def create_story(cls, world: World, **kwargs) -> Story:

        world = cls._normalize_world_arg(world)
        sm = world.script_manager

        story_globals = sm.get_story_globals()                      # creates a copy
        if story_globals:
            kwargs['locals'] = story_globals
        story = Story(world=world, **kwargs)  # kwargs may include 'user'

        def _structure_node_data(key, default_cls):
            data = sm.get_unstructured(key)
            for item in data:
                item.setdefault('obj_cls', default_cls)
                # todo: need to tag kwargs with this world/domain to trigger plugin funcs
                SelfFactoringHandler.create_node(**item, graph=story)

        _structure_node_data('scenes', Scene)
        _structure_node_data('actors', Actor)

        return story

    ###########################################################################
    # World Dev API
    ###########################################################################

    @classmethod
    def get_scene_list(cls, world: World) -> WorldSceneList:
        world = cls._normalize_world_arg(world)
        sm = world.script_manager

        scenes = sm.get_unstructured("scenes")
        items = []
        for i, s in enumerate(scenes):
            data = {'key': s['label'],
                    'value': s.get('title', f'Scene {i}')}
            if x := s.get('style_dict', {}).get('color'):
                data['style_dict'] = {'color': x}
            items.append(data)
        res = [WorldSceneItem(**v) for v in items]
        return res
