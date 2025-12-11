from typing import Optional
from uuid import UUID

import attr

from tangl.core import Node
from tangl.core.factory import AutomorphicMixin
from tangl.core.services import TraversableMixin, RenderableMixin, AutoTraverse

@attr.s
class Action(TraversableMixin, AutomorphicMixin, Node):

    # todo: remove DUMMY default - set to None to validate content
    target_block_id: Optional[str|UUID|TraversableMixin] = attr.ib(
        default='DUMMY',
        validator=attr.validators.instance_of((str, UUID, TraversableMixin)))

    # def __init__(self, *args, **kwargs):
    #     if not kwargs and len(args) == 1 and isinstance( args[0], str ):
    #         kwargs = { 'target_block_id': args[0] }
    #         args = ()
    #     self.__attrs_init__(*args, **kwargs)

    auto_trigger: Optional[AutoTraverse] = attr.ib(default=None)
    # If this is an automatically triggered action, set to ON_ENTER or ON_EXIT

    @property
    def target_block(self) -> TraversableMixin:
        if isinstance( self.target_block_id, TraversableMixin ):
            return self.target_block_id
        if self.target_block_id in self.index:
            return self.index.find(self.target_block_id)
        expanded_id = self.path.split("/")[:-2] + [self.target_block_id]
        expanded_id = "/".join(expanded_id)
        if expanded_id in self.index:
            return self.index.find(expanded_id)
        if self.target_block_id == "DUMMY":
            print(f"Routing around missing key in {self.path}")
            return self.index.find("main_menu/start")
        raise KeyError(f"No block found with id {self.target_block_id}")

    def is_enterable(self, **kwargs):
        return super().is_enterable(**kwargs) and self.target_block.is_enterable(**kwargs)

    def enter(self, **kwargs):
        super().enter()
        if self.target_block:
            return self.target_block.enter()
        else:
            raise Exception("Action target_block is None. Must point to a valid block ID.")

    @classmethod
    def create_from_story_node(cls, story_node: RenderableMixin ):
        from .scene import Scene, Block
        if not isinstance(story_node, (Block, Scene)):
            raise TypeError(f"Story node must be of type Block or Scene, not {type(story_node).__name__}")

        # Set the target_block_id as the id of the given story_node
        # Set the label based on the "action_label" variable in the story node's namespace
        action = cls(
            uid=f"dy-ac-{story_node.path}",
            label=story_node.locals.get("action_label", story_node.label),
            target_block_id=story_node.guid)

        return action
