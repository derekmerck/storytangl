from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import Field

from tangl.core import Node, Graph, HasContext
from tangl.world.world import World

if TYPE_CHECKING:
    from .story_graph import Story

class StoryNode(HasContext, Node):

    graph: Graph = Field(None, json_schema_extra={'cmp': False})
    # todo: Update required type -> Story, but circular ref? Put all in one file?

    dirty: bool = False  # flag for when a story node has been tampered with

    @property
    def story(self) -> Story:
        return self.graph

    @property
    def world(self) -> World:
        return self.story.world
