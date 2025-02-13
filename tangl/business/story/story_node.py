from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import Field

from tangl.business.core import Graph, Node
from tangl.business.core.handlers import HasContext

if TYPE_CHECKING:
    from tangl.business.world.world import World
else:
    from tangl.business.core import Singleton as World

class StoryNode(HasContext, Node):

    graph: Story = Field(None, json_schema_extra={'cmp': False})
    # Update required type

    @property
    def story(self) -> Story:
        return self.graph

    @property
    def world(self) -> World:
        return self.story.world


class Story(HasContext, Graph[StoryNode]):

    world: World = None
    cursor_id: UUID = None

    @property
    def cursor(self) -> StoryNode:  # todo: should be a traversable story node, no less
        return self[self.cursor_id]
