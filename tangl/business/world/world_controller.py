from __future__ import annotations
from typing import TYPE_CHECKING
from tangl.type_hints import Identifier
from tangl.service.api_endpoints import ApiEndpoint, MethodType, AccessLevel, HasApiEndpoints, ResponseType
from tangl.business.content.media.media_record import MediaDataType, MediaRecord
from .world import World, WorldInfo

if TYPE_CHECKING:
    from tangl.service.user import User
    from tangl.business.story.story_graph import Story
else:
    # Fallbacks for endpoint type hinting
    class User: pass
    class Story: pass

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

    Wrapping the methods with ApiEndpoint provides the ServiceManager
    class with hints for creating appropriate service-layer endpoints
    with context.
    """

    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED)
    def load_world(self, **sources):
        raise NotImplementedError

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.RESTRICTED)
    def unload_world(self, world: World):
        World.clear_instance(world.label)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC)
    def get_world_info(self, world: World, **kwargs) -> WorldInfo:
        return world.get_info(**kwargs)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.PUBLIC)
    def get_world_media(self, world: World, media: MediaRecord | Identifier, **kwargs) -> MediaDataType:
        if isinstance(media, Identifier):
            media = world.media_registry.find_one(alias=media)
        return media.get_content(**kwargs)

    @ApiEndpoint.annotate(
        preprocessors=[_dereference_world_id],
        access_level=AccessLevel.USER,
        group="user")
    def create_story(self, world: World, user: User = None, **kwargs) -> Story:
        # explicitly including the user kwarg is redundant, but it signals the
        # service manager logic to dereference a calling user for this method.
        return world.create_story(user=user, **kwargs)

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        group="system")
    def list_worlds(self):
        return { v.label: v.name for v in World.all_instances() }
