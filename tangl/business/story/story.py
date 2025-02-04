from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID

from tangl.core import Graph, Node
from tangl.core.handlers import HasContext

if TYPE_CHECKING:
    from tangl.business.world.world import World
else:
    from tangl.core import Singleton as World

class StoryNode(HasContext, Node):

    @property
    def story(self) -> Story:
        return self.graph

    @property
    def world(self):
        return self.story.world


class Story(HasContext, Graph[StoryNode]):

    world: World = None
    cursor_id: UUID = None

    @property
    def cursor(self) -> StoryNode:  # todo: should be a traversable story node, no less
        return self[self.cursor_id]

    # def get_scenes(self):
    #     from .scene import Scene
    #     self.find(has_cls=Scene)
