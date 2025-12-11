from __future__ import annotations

import logging

from typing import Iterable
from logging import getLogger

from tangl.entity.mixins import Renderable, RenderHandler, HasEffects, Conditional
from tangl.graph.mixins import TraversableNode
from tangl.media import HasMedia

from tangl.story.story import StoryNode
from tangl.story.journal_models import JournalStoryUpdate
from .action import Action

logger = getLogger("tangl.block")
logger.setLevel(logging.WARNING)

class Block(HasMedia, TraversableNode, Renderable, HasEffects, Conditional, StoryNode):
    """
    Blocks are traversable story-nodes that represent passages or narrative
    beats within a scene. Blocks are traverseable, so they can contain multiple
    edges to other blocks, edges may be triggered by Action-choices, or triggered
    automatically on enter or exit.

    A block produces a single JournalEntry on traversal.

    :ivar content: The narrative content of the block.
    :ivar actions: A list of actions that belong to this block.
    :ivar redirects: A list of edges that may be triggered on _entry_.
    :ivar continues: A list of edges that may be triggered on _exit_.
    """

    # Casts type annotations for factory inspection
    @property
    def actions(self) -> Iterable[Action]:
        # re-order from children set by label act_0, act_1, etc...
        return self.find_children(Action, lambda x: x.activation is None, sort_key='label')

    @property
    def continues(self) -> Iterable[Action]:
        return self.find_children(Action, lambda x: x.activation == "exit", sort_key='label')

    @property
    def redirects(self) -> Iterable[Action]:
        return self.find_children(Action, lambda x: x.activation == "enter", sort_key='label')

    @RenderHandler.strategy
    def _include_actions(self):
        logger.debug("including block choices...")
        return {'actions': [ a.render() for a in self.actions if a.available() ]}

    def _unlink_dynamic_actions(self):
        """Sub-classes with dynamically-assigned actions should invoke this when recomputing dynamics"""
        self.discard_children(Action, has_tags=['dynamic'], delete_node=True)

    # def render(self) -> JournalStoryUpdate:
    #     res = super().render()
    #     return JournalStoryUpdate(**res)

    # @DialogHandler.strategy
    # def _parse_dialog(self):
    #     ...



