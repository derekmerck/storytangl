from pydantic import Field

from tangl.type_hints import UniqueLabel, StringMap
from tangl.business.core import DynamicEdge
from tangl.business.story.story_node import StoryNode
from .actor import Actor

class Role(StoryNode, DynamicEdge[Actor]):

    successor_ref: UniqueLabel = Field(None, alias="actor_ref")
    successor_template: StringMap = Field(None, alias="actor_template")
    successor_criteria: StringMap = Field(None, alias="actor_criteria")

