from typing import Optional, Any

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.core import DynamicEdge, HasEffects, Renderable, on_render, TraversableEdge
from tangl.story.story_node import StoryNode
from .block import Block

class Action(HasEffects, TraversableEdge, Renderable, DynamicEdge[Block], StoryNode):

    successor_ref: Identifier = Field(..., alias="next")
    # Using successor_template or criteria will _probably_ work, but is currently undefined.

    payload: Optional[Any] = None

    @on_render.register()
    def _provide_callback_payload(self, payload: Any = None, **context):
        # This is useful if you want to re-use the same action with different parameters,
        # or set a parameter on the client end and return it via an action cb
        payload = payload or self.payload
        if payload is not None:
            return {'payload': payload}
