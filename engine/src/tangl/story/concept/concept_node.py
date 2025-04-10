# concepts are non-traversable nodes that can be linked through dynamic edges

from tangl.core.handlers import Associating
from tangl.core.graph import DynamicEdge
from tangl.story.story_graph import Story
from tangl.story.story_node import StoryNode

class ConceptNode(Associating, StoryNode):
    ...

class ConceptLink(DynamicEdge[ConceptNode]):
    ...

class HasConcepts:

    story: Story

    def concepts(self) -> list[ConceptNode]:
        self.story.find(obj_cls=ConceptNode)
