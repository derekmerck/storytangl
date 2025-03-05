from typing import TYPE_CHECKING
from tangl.business.core.handlers import HasConditions, HasEffects, Renderable, TraversableNode
from tangl.business.story.story_node import StoryNode

if TYPE_CHECKING:
    from .action import Action

class Block(HasConditions, HasEffects, TraversableNode, Renderable, StoryNode):

    @property
    def actions(self) -> list[Action]:
        from .action import Action
        return self.find_children(has_cls=Action)
