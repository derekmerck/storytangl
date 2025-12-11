from logging import getLogger
from typing import Optional

import pydantic

from tangl.graph import Node
from tangl.entity.mixins import Renderable, HasEffects, Conditional
from tangl.graph.mixins import Edge
from tangl.story.story import StoryNode

logger = getLogger("tangl.action")

class Action(Renderable, HasEffects, Conditional, Edge, StoryNode):

    text: Optional[str] = "continue"

    @classmethod
    def from_node(cls, node: StoryNode):
        # todo: This type of action suffers from indeterminate namespace inheritance,
        #       should available() be based on the target node or the current
        #       node's availability or both?
        return cls(
            text = node.locals.get("action_text", node.text if node.text else node.label),
            successor_ref = node,
            graph = node.graph,
            tags=['dynamic']
        )

    @pydantic.field_validator('successor_ref', mode='before')
    @classmethod
    def _convert_successor_to_ref(cls, value):
        if isinstance(value, Node):
            return value.uid
        return value

    @property
    def successor(self):
        if self.successor_ref:
            key_candidates = [ self.successor_ref ]
            if self.root:
                key_candidates.append( f"{self.root.label}/{self.successor_ref}" )
            for key in key_candidates:
                try:
                    return self.graph.get_node( key )
                except KeyError:
                    pass
            raise KeyError(f"Can't find successor called {key_candidates}")
