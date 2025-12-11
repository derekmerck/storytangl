from uuid import UUID
from typing import Any, TYPE_CHECKING
import logging

from tangl.type_hints import UniqueLabel, StringMap
from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity.handlers import ConditionHandler, EffectHandler
from tangl.core.graph.handlers import TraversalHandler, TraversableNode
from tangl.journal import JournalHandler, JournalEntry
from .story_node import Story
from .story_info_models import StoryInfo

if TYPE_CHECKING:
    from .scene import Action
else:
    from tangl.core.graph import Node as Action

logger = logging.getLogger(__name__)


class StoryHandler(TraversalHandler, JournalHandler):
    """
    Provides basic methods for interacting with Story instances.

    client api:
      - get_journal_entry(range)
      - get_story_info(features)
      - do_action(action_id, payload)

    dev api:
      - goto_node(node_id)
      - check_expr(expression)
      - apply_expr(expression)

    supports hooks:
      - on_do_action
      - on_get_story_info
    """

    ###########################################################################
    # Story Client API
    ###########################################################################

    @classmethod
    def do_action(cls, story: Story, action: UUID | Action, payload: dict = None) -> None:
        """
        Execute an available story action, use the payload kwarg to pass back specifiers
        or quantifiers for generic actions.
        """
        if isinstance(action, (UUID, str)):
            action = story.get_node(action)
        logger.debug(f"found action: {action!r}")
        payload = payload or {}
        if new_action := cls.execute_task(story, 'on_do_action', **payload, result_mode="first"):
            action = new_action
        logger.debug(f"resolved action: {action!r}")
        # todo: pass payload to on_do_action handler or on_enter handler?  Games can hook on_do_action, which is resolved _before_ on_enter from follow-edge??  Or should payload be processed as part of the game on_enter handler?
        story.follow_edge(action)

    @classmethod
    def get_story_info(cls, story: Story, features: dict = None) -> StoryInfo:
        """
        Get the current story status, use features kwarg to request special views
        such as current scene title, player stats, sidebar avatar, sandbox overview, etc.
        """
        # todo: Not quite right b/c it must be returned as an ordered dict of label: (value, style) records
        features = features or {}
        return cls.execute_task(story, 'on_get_story_info', **features, result_mode="merge")

    @classmethod
    def get_journal_entry(cls, story: Story, which: int = -1) -> JournalEntry:
        """
        The latest entry is returned by default.
        """
        return super().get_journal_entry(story.journal, which)

    ###########################################################################
    # Story Developer API
    ###########################################################################

    @classmethod
    def goto_node(cls, story: Story, node: UUID | UniqueLabel | TraversableNode) -> None:
        """This is only used for testing and debugging purposes.  Jumping directly to a node
        without following a link can result in unexpected behaviors."""
        if isinstance(node, UUID | UniqueLabel):
            node = story.get_node(node)
        super().goto_node(story, node)

    @classmethod
    def check_expr(cls, story: Story, expr: str) -> Any:
        """This is only used for testing and debugging purposes.  Evaluating state
        outside of a specific context can yield non-deterministic results."""
        return ConditionHandler.check_expr(expr, story.get_namespace())

    @classmethod
    def apply_expr(cls, story: Story, expr: str):
        """This is only used for testing and debugging purposes.  Updating state
        outside of a specific context can result in non-tenable game states."""
        EffectHandler.apply_effect(expr, story.get_namespace())

    ###########################################################################
    # Task Decorators
    ###########################################################################

    # @BaseHandler.task_signature
    # def on_do_action(story: Story, action: Action = Action, **kwargs):
    #     ...

    @classmethod
    def do_action_strategy(cls, task_id: UniqueLabel = "on_do_action",
                           domain: UniqueLabel = "global",
                           priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)


    # @BaseHandler.task_signature
    # def on_get_story_info(story: Story, **kwargs) -> StoryInfo:
    #     ...

    @classmethod
    def get_story_info_strategy(cls, task_id: UniqueLabel = "on_get_story_info",
                                domain: UniqueLabel = "global",
                                priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)

