from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import Field

from tangl.core import Node
from tangl.core import HasContext
from tangl.world.world import World

if TYPE_CHECKING:
    from .story_graph import Story

class StoryNode(HasContext, Node):

    graph: Story = Field(None, json_schema_extra={'cmp': False})
    # Update required type

    dirty: bool = False  # flag for when a story node has been tampered with

    @property
    def story(self) -> Story:
        return self.graph

    @property
    def world(self) -> World:
        return self.story.world
