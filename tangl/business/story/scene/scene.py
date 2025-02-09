
from tangl.core.entity.handlers import HasEffects, HasConditions
from tangl.core.graph.handlers import Traversable

from tangl.business.story.story_node import StoryNode
from tangl.business.story.actor import Actor, Role
from tangl.business.story.place import Place, Location
from .block import Block

class Scene(HasConditions, HasEffects, Traversable, StoryNode):

    @property
    def locations(self) -> list[Location]:
        return self.find_children(has_cls=Location)

    @property
    def roles(self) -> list[Role]:
        return self.find_children(has_cls=Role)

    @property
    def blocks(self) -> list[Block]:
        return self.find_children(has_cls=Block)
