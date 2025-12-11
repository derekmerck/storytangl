from typing import TYPE_CHECKING, TypeVar, Type, Any
import logging

from tangl.type_hints import Pathlike, UniqueLabel
from tangl.resource_registry.resource_registry import ResourceRegistry, ResourceLocation
from tangl.graph.mixins import PluginHandler
from tangl.script import ScriptManager
from .response_models import WorldInfo, WorldListItem, WorldList, WorldSceneItem, WorldSceneList
from .world import World

if TYPE_CHECKING:
    from tangl.user import User
    from tangl.story.story import Story

WorldType = TypeVar('WorldType', bound=World)
Worldlike = World | UniqueLabel

logger = logging.getLogger("tangl.world.handler")

class WorldHandler:
    """
    Provides standard methods for service-layer interactions with a world object.

    public api:
      - get_world_list -> list[kv]
      - get_world_info -> dict

    client api:
      - create_story   -> Story

    backend api:
      - create_world   -> World

    dev api:
      - get_scene_list -> list[kv]
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
    def get_world_list(cls) -> WorldList:
        worlds = World._instances.values()
        infos = [ w.get_info() for w in worlds ]
        print(infos)
        items = []
        for info in infos:
            data = {'label': info['label'],
                    'text': info['title']}
            if x := info.get('ui_config', {}).get('brand_color'):
                data['style_dict'] = {'color': x}
            items.append( data )
        res = [ WorldListItem(**v) for v in items ]
        return res

    @classmethod
    def get_world_info(cls, world: Worldlike) -> WorldInfo:
        world = cls._normalize_world_arg(world)
        data = world.get_info()
        return WorldInfo( **data )

    ###########################################################################
    # World Client API
    ###########################################################################

    @classmethod
    def create_story(cls, world: Worldlike, user: 'User' = None, **kwargs) -> 'Story':
        world = cls._normalize_world_arg(world)
        return world.create_graph(user=user, **kwargs)

    ###########################################################################
    # World Backend API
    ###########################################################################

    @classmethod
    def create_world(cls,
                     label: str,
                     world_cls: Type[WorldType] = World,
                     script_manager: ScriptManager = None,
                     resource_registry: ResourceRegistry = None,

                     source_package: str = None,
                     resource_package: str = "resources",

                     script_mgr_cls: Type[ScriptManager] = ScriptManager,
                     # Multifile-format
                     sections: dict[str, [list[Pathlike]]] = None,
                     metadata: dict | Pathlike = "../info.yaml",
                     # Singlefile-format
                     script_file: Pathlike = None,

                     resource_registry_cls: Type[ResourceRegistry] = ResourceRegistry,
                     media_file_locations: list[str] = ("media"),

                     scene_art_forge: 'SvgForge' = None,
                     scene_art_file: Pathlike = "scene_art.forge.svg",

                     plugins: Any = None) -> WorldType:

        if label in World._instances:
            return World.get_instance(label)

        resources = ".".join([source_package or label, resource_package])

        if not script_manager:
            if script_file:
                # single-file format
                script_manager = script_mgr_cls.from_file(
                    resources=resources,
                    script_file=script_file,
                )

            else:
                # multi-file format
                if not sections:
                    sections = {
                        "scenes": ["scenes/*.yaml"],
                        "actors": ["actors/*.yaml"],
                        "assets": ["assets/*.yaml"],
                        "templates": ["templates/*.yaml"]
                    }

                script_manager = script_mgr_cls.from_files(
                    resources=resources,
                    sections=sections,
                    metadata=metadata
                )

        if not resource_registry:
            resource_registry = resource_registry_cls(label=label)  # type: ResourceRegistry
            # for media_loc in media_resource_locations:
            #     rd.add_file_location(base_path=resources / media_loc )

        if not scene_art_forge:
            try:
                from tangl.media.svgforge import SvgForge
                scene_art_forge = SvgForge(
                    label=label,
                    resources=resources,
                    source_fp= "media/" + scene_art_file,
                )
            except OSError:  # Couldn't find a source
                logger.warning(f"Could not find svg scene art for {label}")
                pass

        world = world_cls(label=label,
                          plugins=plugins,
                          script_manager=script_manager,
                          media_resources=resource_registry,
                          scene_art_forge=scene_art_forge)
        if hasattr(world, 'pm'):
            PluginHandler.on_init_entity(world.pm, world)
        return world

    ###########################################################################
    # World Dev API
    ###########################################################################

    @classmethod
    def get_scene_list(cls, world: Worldlike) -> WorldSceneList:
        # Useful for debugging
        world = cls._normalize_world_arg(world)
        scenes = world.get_scenes()
        data = [ {'label': sc['label'],
                  'text': sc.get('text', 'Missing Title')} for sc in scenes ]
        # todo: include icon, color or other indicators...
        # logger.debug(str(data))
        res = [ WorldSceneItem( **v ) for v in data ]
        return res

