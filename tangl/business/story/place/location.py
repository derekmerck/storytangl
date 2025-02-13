from pydantic import Field

from tangl.type_hints import UniqueLabel, StringMap
from tangl.business.core import DynamicEdge
from tangl.business.story.story_node import StoryNode
from .place import Place

class Location(StoryNode, DynamicEdge[Place]):

    successor_ref: UniqueLabel = Field(None, alias="place_ref")
    successor_template: StringMap = Field(None, alias="place_template")
    successor_criteria: StringMap = Field(None, alias="place_criteria")

