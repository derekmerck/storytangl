from typing import Optional, Any

from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.core.graph import DynamicEdge
from tangl.core.entity.handlers import HasConditions, HasEffects, Renderable, on_render
from tangl.core.graph.handlers import Traversable
from tangl.business.story.story_node import StoryNode
from .block import Block

class Action(HasConditions, HasEffects, Traversable, Renderable, DynamicEdge[Block], StoryNode):

    successor_ref: UniqueLabel = Field(None, alias="next")
    # Using successor_template or criteria will _probably_ work, but is currently undefined.

    default_payload: Optional[Any] = None

    @on_render.register()
    def _provide_callback_payload(self, payload: Any = None, **context):
        # This is useful if you want to re-use the same action with different parameters,
        # or set a parameter on the client end and return it via an action cb
        payload = payload or self.default_payload
        return {'payload': payload}


