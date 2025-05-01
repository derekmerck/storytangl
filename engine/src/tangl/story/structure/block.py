from __future__ import annotations
from typing import TYPE_CHECKING
from tangl.core import Available, HasConditions, HasEffects, Renderable, TraversableNode, HasScopedContext
from tangl.story.story_node import StoryNode

if TYPE_CHECKING:
    from .action import Action

class Block(Available, HasConditions, HasEffects, TraversableNode, HasScopedContext, Renderable, StoryNode):

    @property
    def actions(self) -> list[Action]:
        from .action import Action
        return self.find_children(has_cls=Action)

    # @on_render.register()
    # def _include_choices(self, **context):
    #     choices = []
    #     for action in self.actions:
    #         choices.append( action.render(**context) )
    #     return choices
