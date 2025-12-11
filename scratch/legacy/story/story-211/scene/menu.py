from __future__ import annotations
import logging
import inspect

from typing import Iterable

from pydantic import Field, field_validator

from tangl.type_hints import Tags
from tangl.entity import BaseEntityHandler
from tangl.graph import Node
from tangl.graph.mixins import TraversableNode
from .block import Block
from .action import Action

logger = logging.getLogger("tangl.story.menu")

class MenuActionHandler(BaseEntityHandler):

    default_strategy_annotation = "is_menu_action_strategy"

    @classmethod
    def get_menu_actions(cls, node: Menu) -> Iterable[Action]:
        node._unlink_dynamic_actions()  # clear existing actions
        blocks = cls.invoke_strategies(node)[0]
        actions = [ Action.from_node(b) for b in blocks ]
        return actions


class Menu(Block):
    """
    Menus are Blocks that can dynamically add actions based on other story nodes,
    for example, a menu block that automatically adds actions pointing to every
    scene's start bock, or a menu block pointing to other blocks with specific
    tags.

    It takes 2 extra parameters:

    :param with_type: Traversable class that target nodes must subclass (default is Block)
    :param with_tags: A set of tags that target nodes must match
    """

    with_type: type[TraversableNode] = Block   # include scene blocks only or story-wide search

    @field_validator("with_type", mode="before")
    @classmethod
    def _deref_with_type(cls, value):
        if isinstance(value, str):
            node_cls = Node.get_subclass_by_name(value)
            if not node_cls:
                logger.error(Node.get_all_subclasses())
                raise TypeError(f"Unable to deref {value}")
            return node_cls
        return value

    with_tags: Tags = Field(default_factory=set)

    @MenuActionHandler.strategy
    def _get_tagged_blocks(self):
        logger.debug( f"trying to find {self.with_type} and {self.with_tags}")
        return list( self.story.find_nodes(self.with_type, has_tags=self.with_tags) )

    @property
    def actions(self) -> Iterable[Action]:
        return MenuActionHandler.get_menu_actions(self)

    # todo: if no actions available, return redirect on enter if possible (skip)
    # def enter(self):
    #     if not self.actions or not any([ a.available() for a in self.actions ]):
    #         # trigger any available continue ...

