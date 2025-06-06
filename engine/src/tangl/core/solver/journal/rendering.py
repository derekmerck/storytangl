from typing import Any

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.handler import HandlerRegistry
from ..feature_nodes import ContentFragment


on_render_content = HandlerRegistry(label='on_render_content', default_aggregation_strategy="pipeline")

class Renderable(Entity):

    content: Any = None

    @on_render_content.register()
    def _provide_content(self, ctx: StringMap) -> StringMap:
        return {'content': self.content}

    @on_render_content.register(priority=100)  # last
    def _assemble_fragments(self, ctx: StringMap) -> list[ContentFragment]:
        result = ctx.pop("result", None)
        return result

    def render_content(self, ctx: StringMap) -> list[ContentFragment]:
        return on_render_content.execute_all(self, ctx=ctx)
