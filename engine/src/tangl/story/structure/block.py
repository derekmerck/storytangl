from __future__ import annotations
from typing import TYPE_CHECKING
from tangl.core import Available, HasConditions, HasEffects, Renderable, TraversableNode, HasScopedContext
from tangl.story.story_node import StoryNode

if TYPE_CHECKING:
    from .action import Action

class Block(Available, HasConditions, HasEffects, TraversableNode, HasScopedContext, Renderable, StoryNode):
    """
    Blocks are traversable story-nodes that represent passages or narrative
    beats within a scene. Blocks are traverseable, so they can contain multiple
    edges to other blocks, edges may be triggered by Action-choices, or triggered
    automatically on enter or exit.

    Each block generates a single JournalEntry on traversal.

    :ivar text: The text of the block.
    :ivar actions: A list of actions that belong to this block.
    :ivar redirects: A list of edges that may be triggered on _entry_.
    :ivar continues: A list of edges that may be triggered on _exit_.
    """
    # journal_item_cls: ClassVar[Type[BlockJournalItem]] = BlockJournalItem
    # blocks are structure nodes that project to journal items

    @property
    def actions(self) -> list[Action]:
        from .action import Action
        return self.find_children(has_cls=Action)

    # @property
    # def actions(self) -> list[Action]:
    #     return self.find_children(Action, lambda x: x.activation is None, sort_key='label')
    #
    # @property
    # def continues(self) -> Iterable[Action]:
    #     return self.find_children(Action, lambda x: x.activation == "last", sort_key='label')
    #
    # @property
    # def redirects(self) -> Iterable[Action]:
    #     return self.find_children(Action, lambda x: x.activation == "first", sort_key='label')

    # Traversable does this automatically
    # @on_render.register()
    # def _include_actions(self, **kwargs) -> dict:
    #     logger.debug("including block choices...")
    #     return {'actions': [ a.render() for a in self.actions if a.available() ]}
