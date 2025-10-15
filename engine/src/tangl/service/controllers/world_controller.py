from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from pathlib import Path

from pydantic import BaseModel

from tangl.service.response.info_response.world_info import WorldList
from tangl.type_hints import Identifier, UnstructuredData
from tangl.service.api_endpoint import ApiEndpoint, MethodType, AccessLevel, HasApiEndpoints, ResponseType
# from tangl.media import MediaDataType, MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula.world import World
from tangl.service.response.info_response import WorldInfo

if TYPE_CHECKING:
    from tangl.service.user import User
    from tangl.story.story import Story
else:
    # Fallbacks for endpoint type hinting
    class User: pass
    class Story: pass

logger = logging.getLogger(__name__)


class WorldInfo(BaseModel):
    # revision, license, etc. should probably just inherit this data from
    # the script manager metadata...
    label: str
    name: str
    # author: str
    # copyright_date: str

    @classmethod
    def from_world(cls, world: World, **kwargs) -> WorldInfo:
        return cls(
            label=world.label,
            name=world.name
        )

def _dereference_world_id(args, kwargs):
    if world_id := kwargs.pop("world_id", None):
        world = World.get_instance(world_id)
        if not world:
            raise ValueError(f"World {world_id} does not exist")
        kwargs["world"] = world  # type: World
    return args, kwargs

class WorldController(HasApiEndpoints):
    """
    This is the library API for the StoryWorld logic implemented as a
    collection of methods.

    public:
    - list all world instances (ro)
    - get info about a world (ro)
    - get world media (maybe rw if new media is generated?)

    client:
    - create a new story from a world (rw)

    restricted:
    - load a world singleton from source (rw)
    - unload a world (rw)
    - list all scenes in a world (ro)

    Wrapping the methods with ApiEndpoint provides the ServiceManager
    class with hints for creating appropriate service-layer endpoints
    with context.
    """

    ###########################################################################
    # World Public API
    ###########################################################################

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        group="system")
    def list_worlds(self) -> list[WorldList]:
        # The world list is formatted as content fragments and can be interpreted
        # as an ordered, styled list
        # It is not strictly necessary, as the available worlds can be learned from
        # system_info, and each world could be queried for info to determine it's branding
        # style.  This is a convenience function that provides that info as a single call.
        return { v.label: v.name for v in World.all_instances() }

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC)
    def get_world_info(self, world: World, **kwargs) -> WorldInfo:
        logger.debug(f"Looking for world info {world}")
        return WorldInfo.from_world(world, **kwargs)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC)
    def get_world_media(self, world: World, media: MediaRIT | Identifier, **kwargs) -> MediaDataType:
        if isinstance(media, Identifier):
            media = world.media_registry.find_one(alias=media)
        return media.get_content(**kwargs)


    ###########################################################################
    # World Client API
    ###########################################################################

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.USER,
        group="user")
    def create_story(self, world: World, user: User = None, **kwargs) -> Story:
        # explicitly including the user kwarg is redundant, but it signals the
        # service manager logic to dereference a calling user for this method.
        return world.create_story(user=user, **kwargs)


    ###########################################################################
    # World Restricted API
    ###########################################################################

    # @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED)
    # def load_world(self, **sources):
    #     raise NotImplementedError

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE
    )
    def load_world(self, *, script_path: str | Path = None, script_data: UnstructuredData = None) -> dict[str, str]:
        """Load a world from a script file path."""
        import yaml

        if script_path is not None:
            path = Path(script_path)
            if not path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            with open(path, 'r') as f:
                script_data = yaml.safe_load(f)

        from tangl.story.fabula.script_manager import ScriptManager
        script_manager = ScriptManager.from_data(script_data)
        from tangl.utils.sanitize_str import sanitise_str
        title = script_manager.get_story_metadata().get('title')
        if title is None:
            raise ValueError("World scripts _must_ contain a label or a metadata section with a title")
        label = sanitise_str(title).lower()
        return World(label=label, script_manager=script_manager)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.RESTRICTED)
    def unload_world(self, world: World):
        World.clear_instance(world.label)
