from typing import TYPE_CHECKING
from tangl.core.entity.handlers import HasConditions, HasEffects, Renderable
from tangl.core.graph.handlers import Traversable
from tangl.business.story.story_node import StoryNode

if TYPE_CHECKING:
    from .action import Action

class Block(HasConditions, HasEffects, Traversable, Renderable, StoryNode):

    @property
    def actions(self) -> list[Action]:
        from .action import Action
        return self.find_children(has_cls=Action)
