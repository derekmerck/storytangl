from typing import Any

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.handler import HandlerRegistry
from ..feature_nodes import ContentFragment


render_handler = HandlerRegistry(label='render_handler', default_aggregation_strategy="pipeline")

class Renderable(Entity):

    content: Any = None

    @render_handler.register()
    def _provide_content(self):
        return {'content': self.content}

    @render_handler.register(priority=100)  # last
    def _assemble_fragments(self, ctx: StringMap) -> list[ContentFragment]:
        result = ctx.pop("result", None)
        ...
        return result