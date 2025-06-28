from __future__ import annotations
import logging

from pydantic import Field, field_validator

from tangl.type_hints import Tags, ClassName, Typelike
from tangl.core.handlers import BaseHandler
from tangl.core.entity import Entity
from .block import Block
from .action import Action

logger = logging.getLogger(__name__)


class MenuActionHandler(BaseHandler):

    @classmethod
    def _unlink_dynamic_actions(cls, node: Block):
        """Sub-classes with dynamically-assigned actions should invoke this when recomputing dynamics"""
        node.discard_children(Action, with_tags=['dynamic'], delete_node=True)

    @classmethod
    def get_menu_actions(cls, node: Block) -> list[Action]:
        cls._unlink_dynamic_actions(node)  # clear existing actions
        blocks = cls.execute_task(node,"on_get_actions", result_mode="flatten")
        actions = [ Action.from_node(b) for b in blocks ]
        return actions


class MenuBlock(Block):
    """
    Menus are Blocks that can dynamically add actions based on other story nodes,
    for example, a menu block that automatically adds actions pointing to every
    scene's start bock, or a menu block pointing to other blocks with specific
    tags.

    It takes 2 extra parameters:

    :param with_cls: Traversable class that target nodes must subclass (default is Block)
    :param with_tags: A set of tags that target nodes must match
    """

    with_cls: Typelike = Block
    with_tags: Tags = Field(default_factory=set)
    # within_scene_only: bool = True  # limit search to children of the same root
    # or use special tag like <scene.label>

    @field_validator("with_cls", mode="before")
    @classmethod
    def _deref_with_cls(cls, value):
        # todo: this could/should be centralized by moving it into "graph._filter"
        if isinstance(value, str):
            node_cls = Entity.get_subclass_by_name(value)
            if not node_cls:
                logger.error(Entity.get_all_subclasses())
                raise TypeError(f"Unable to deref {value}")
            return node_cls
        return value

    @property
    def actions(self) -> list[Action]:
        dynamic_actions = MenuActionHandler.get_menu_actions(self)
        return super().actions + dynamic_actions

    @MenuActionHandler.strategy('on_get_actions')
    def _get_tagged_blocks(self):
        logger.debug( f"Searching for actions {self.with_cls} and {self.with_tags}")
        return list( self.story.find_nodes(self.with_cls, with_tags=self.with_tags) )

    # todo: if no actions available, return redirect on enter if possible (skip)
    # def enter(self):
    #     if not self.actions or not any([ a.available() for a in self.actions ]):
    #         # trigger any available continue ...

