from __future__ import annotations
from typing import Iterable
import logging

from tangl.type_hints import StringMap
from tangl.core import HasConditions as Conditional, HasEffects, Renderable, on_render, on_avail, on_gather_context, HandlerPriority, TraversableNode, TraversableEdge
from tangl.core.graph import SimpleEdge
from tangl.core.graph.handlers import TraversalStage
from tangl.journal import JournalingNode
from tangl.story import StoryNode, StoryHandler
from tangl.story.concept import Role, Actor, Location, Setting
# from tangl.story.asset import Assets
from tangl.story.structure import Block

logger = logging.getLogger(__name__)

class Scene(TraversableNode, Renderable, Conditional, HasEffects, JournalingNode, StoryNode):

    def find_entry_node(self: TraversableNode) -> TraversableNode:
        return TraversalHandler.find_entry_node(self.children, node_cls=Block)

    def actor_map(self) -> dict[str, Actor]:
        return { role.label.replace("-", "_"): role.actor for role in self.roles if role.actor }

    def block_map(self) -> dict[str, Block]:
        return { block.label: block for block in self.blocks }

    def child_map(self) -> dict[str, Actor|Block]:
        res = {}
        res.update( self.actor_map() )
        res.update( self.block_map() )
        return res

    @on_gather_context.register()
    def _include_scene_children(self) -> dict[str, StoryNode]:
        return self.child_map()

    def __getattr__(self, item):
        # return items by name in the child map, this provides a
        # 'dot' accessor for blocks and role labels by name
        if x := self.child_map().get(item):
            return x
        return super().__getattr__(item)

    # todo: I think this is not quite right -- it will redirect back to the entry node
    #       even if an explicit target is given when entering the scene as a container,
    #       ike scene1/block2, since the cursor logic doesn't know whether it needs to
    #       resolve a default final destination or not
    @StoryHandler.enter_strategy(priority=TraversalStage.CONTINUING)
    def _continue_to_first_block(self, **kwargs):
        # Scenes are essentially containers and should automatically continue to their first block
        entry_block = StoryHandler.find_entry_node(self.blocks)
        logger.debug("redirecting to first block")
        if not entry_block:
            raise ValueError("Unable to determine entry block")
        edge = SimpleEdge(predecessor=self, successor=entry_block)
        return edge

