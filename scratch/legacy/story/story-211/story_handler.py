from __future__ import annotations
from typing import TYPE_CHECKING
from logging import getLogger
from uuid import UUID

from tangl.type_hints import Uid, UniqueLabel
from tangl.entity.mixins import NamespaceHandler, ConditionHandler, EffectHandler
from tangl.graph.mixins import TraversalHandler
from tangl.journal import JournalHandler
from .response_models import StoryStatus
from .journal_models import JournalStoryUpdate

if TYPE_CHECKING:
    from .scene import Action
    from .story import Story

logger = getLogger("tangl.traversal.story")

class StoryHandler(TraversalHandler):
    """
    Provides standard methods for interacting with a story object.

    client methods:
      - get_update
      - do_action
      - get_status

    dev methods:
      - inspect_node
      - check_expr
      - apply_effect
      - goto_block
    """

    ###########################################################################
    # Story Client API
    ###########################################################################

    @classmethod
    def do_action(cls, story: 'Story', action: 'Action' | UniqueLabel, **kwargs):
        if isinstance(action, UniqueLabel | UUID ):
            action = story.get_node(action)
        return story.follow_edge(edge=action, **kwargs)

    @classmethod
    def get_update(cls, story: 'Story', entry = -1, section = None) -> list[JournalStoryUpdate]:
        if section is not None:
            res = JournalHandler.get_section(story.journal, section)
        else:
            res = JournalHandler.get_entry(story.journal, entry)

        res = [ JournalStoryUpdate(**entry.model_dump()) for entry in res]

        return res

    @classmethod
    def get_status(cls, story: Story) -> StoryStatus:
        # alias for get_traversal_status
        return cls.get_traversal_status(story)

    ###########################################################################
    # Story Dev API
    ###########################################################################

    @classmethod
    def inspect_node(cls, story: 'Story', node_id: Uid):
        return story.get_node(node_id).model_dump()

    @classmethod
    def goto_node(cls, story: 'Story', node_id: Uid):
        """
        Marks story as dirty, achievements off etc.
        """
        next_node = story.get_node(node_id)
        story.dirty = True
        # next_node.forced = True  # This will mark the story as dirty
        JournalHandler.start_new_entry( story.journal )
        logger.debug(f"Going to node {node_id}")
        super().goto_node(story, next_node)

    @classmethod
    def check_expr(cls, story: 'Story', expr: str):
        ns = NamespaceHandler.get_namespace(story)
        return ConditionHandler.check_expr(expr, ns)

    @classmethod
    def apply_effect(cls, story: 'Story', effect: str):
        """
        Marks story as dirty, achievements off, etc.
        """
        story.dirty = True
        ns = NamespaceHandler.get_namespace(story)
        return EffectHandler.apply_effect(effect, ns)

    ###########################################################################
    # Overrides
    ###########################################################################

    # @classmethod
    # def enter(cls, graph: 'Story', entry_node: 'StoryNode' = None):
    #     """
    #     Stories have multiple sub-graphs (Scenes), so we want to determine the entry scene.
    #     Entering the scene will automatically find and enter the first block.
    #     """
    #     if not entry_node:
    #         from .scene import Scene
    #         entry_node = cls.find_entry_node(graph.find_nodes(Scene))
    #     return super().enter(graph, entry_node)
