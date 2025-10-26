import logging

from tangl.core import HasEffects, HasConditions, TraversableNode, on_gather_context, on_avail

from ..story_node import StoryNode
from tangl.story.concepts.actor import Role
from tangl.story.concepts.location import Setting
from tangl.story.episode.block import Block

logger = logging.getLogger(__name__)

class Scene(HasConditions, HasEffects, TraversableNode, StoryNode):
    """
    Scenes and related elements are narratively traversable story nodes. Actions are edges
    that connect them.  As scene elements are traversed, the world state can be updated and
    narrative output is rendered to the story journal.

    A scene is a root node for a specific narrative arc, and it can contain multiple Blocks
    and Roles. It provides methods to add a block or role and also to get its namespace.

    {class}`Scenes <Scene>` are collections of {class}`blocks <Block>` (story beats),
    {class}`roles <Role>` (npcs), and {class}`locations <Location>`.

    :var  label: The scene title, used on first block
    :ivar is_entry: indicates the entry point for the story
    :ivar blocks: A list of blocks that belong to this scene.
    :ivar roles: A list of roles that belong to this scene.
    """

    @property
    def settings(self) -> list[Setting]:
        # These are indirect links to Places
        return self.find_children(has_cls=Setting)

    @property
    def roles(self) -> list[Role]:
        # These are indirect links to Actors
        return self.find_children(has_cls=Role)

    @property
    def blocks(self) -> list[Block]:
        return self.find_children(has_cls=Block)

    @on_gather_context.register()
    def _provide_actors(self, **context):
        res = {}
        if len(self.roles) == 1:
            logger.debug(self.roles[0].actor)
            res['actor'] = self.roles[0].successor
        res |= { v.label: v.successor for v in self.roles if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_locations(self, **context):
        res = {}
        if len(self.settings) == 1:
            res['location'] = self.settings[0].successor
        res |= { v.label: v.successor for v in self.settings if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_self(self, **context):
        return { 'scene': self }

    # todo: This won't work unless we get rid of the base on_render content->content entry?
    # @on_render.register()
    # def _text_is_title(self) -> StringMap:
    #     if self.content:
    #         return { "title": self.content }

    def cast(self) -> bool:
        cast_roles = [x.cast() for x in self.roles]
        return all(cast_roles)

    @on_avail.register()
    def _is_cast(self):
        # testing availability will attempt to cast all uncast roles
        return self.cast()

    def scout(self) -> bool:
        scout_locs = [x.scout() for x in self.locations]
        return all(scout_locs)

    @on_avail.register()
    def _is_scouted(self):
        # testing availability will attempt to scout all unscouted locs
        return self.cast()
