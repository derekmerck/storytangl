from typing import Iterable, Mapping
import logging

from pydantic import model_validator

from tangl.entity.mixins import HasEffects, Conditional, Renderable, AvailabilityHandler, NamespaceHandler
from tangl.graph.mixins import TraversableNode, TraversalHandler, Edge
from tangl.story.story import StoryNode
from tangl.story.actor import Role, Actor
from tangl.story.scene import Block, Action

logger = logging.getLogger("tangl.scene")

class Scene(TraversableNode, HasEffects, Conditional, Renderable, StoryNode):
    """
    The Scene class extends the StoryNode class and represents a scene in a narrative structure.

    A scene is a root node for a specific narrative arc, and it can contain multiple Blocks
    and Roles. It provides methods to add a block or role and also to get its namespace.

    {class}`Scenes <Scene>` are collections of {class}`blocks <Block>` (story beats), {class}`roles <Role>` (npcs), and {class}`locations <Location>`.

    :ivar is_entry: indicates the entry point for the story
    :var  label: The scene title, used on first block
    :ivar blocks: A list of blocks that belong to this scene.
    :ivar roles: A list of roles that belong to this scene.
    """

    @property
    def title(self) -> str:
        return self.text

    @property
    def blocks(self) -> Iterable[Block]:
        return self.find_children(Block)

    @property
    def roles(self) -> Iterable[Role]:
        return self.find_children(Role)

    def cast(self) -> bool:
        cast_roles = [x.cast() for x in self.roles]
        return all(cast_roles)

    @AvailabilityHandler.strategy
    def _is_cast(self):
        # testing availability will attempt to cast all uncast roles
        return self.cast()

    def actor_map(self) -> dict[str, Actor]:
        return { role.label.replace("-", "_"): role.actor for role in self.roles if role.actor }

    def block_map(self) -> dict[str, Block]:
        return { block.label: block for block in self.blocks }

    def child_map(self) -> dict[str, Actor|Block]:
        res = {}
        res.update( self.actor_map() )
        res.update( self.block_map() )
        return res

    @NamespaceHandler.strategy
    def _include_scene_children(self) -> dict[str, StoryNode]:
        return self.child_map()

    def __getattr__(self, item):
        # return items by name in the child map, this provides a
        # 'dot' accessor for blocks and role labels by name
        if x := self.child_map().get(item):
            return x
        return super().__getattr__(item)

    @TraversalHandler.enter_strategy
    def _enter_first_block(self, with_edge: Action = None):
        # Redirect to initial block
        logger.debug("redirecting to first block")
        entry_block = TraversalHandler.find_entry_node(self.blocks)
        if not entry_block:
            raise ValueError("Unable to determine entry block")
        # Don't simulate an edge to force a context update, it can result in a recursion error
        self.graph.cursor = entry_block
        return TraversalHandler.enter(entry_block, with_edge=with_edge)
    _enter_first_block.strategy_priority = 85
    # _after_ rendering your own title (80) but before checking continues (90)

