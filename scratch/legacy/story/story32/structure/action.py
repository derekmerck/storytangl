from typing import Optional, Any

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.core import DynamicEdge, HasEffects, Renderable, on_render, TraversableEdge
from tangl.story.story_node import StoryNode
from .block import Block

class Action(HasEffects, TraversableEdge, Renderable, DynamicEdge[Block], StoryNode):

    successor_ref: Identifier = Field(..., alias="next")
    # Using successor_template or criteria will _probably_ work, but is currently undefined.

    content: Optional[str] = "continue"
    payload: Optional[Any] = None

    @on_render.register()
    def _provide_callback_payload(self, payload: Any = None, **context):
        # This is useful if you want to re-use the same action with different parameters,
        # or set a parameter on the client end and return it via an action cb
        payload = payload or self.payload
        if payload is not None:
            return {'payload': payload}

    @classmethod
    def from_node(cls, node: StoryNode):
        # todo: This type of action suffers from indeterminate namespace inheritance,
        #       should available() be based on the target node or the current
        #       node's availability or both?
        return cls(
            content = node.locals.get("action_text", node.label),
            successor = node,
            graph = node.graph,
            tags={'dynamic'}
        )

    # before find by alias was standardized
    # @property
    # def successor(self):
    #     if self.successor_ref:
    #         key_candidates = [ self.successor_ref ]
    #         if self.root:
    #             key_candidates.append( f"{self.root.label}/{self.successor_ref}" )
    #         for key in key_candidates:
    #             try:
    #                 return self.graph.get_node( key )
    #             except KeyError:
    #                 pass
    #         raise KeyError(f"Can't find successor called {key_candidates}")
