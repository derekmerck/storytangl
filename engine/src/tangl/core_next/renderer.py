from .fragment import ContentFragment
from .context_builder import ContextView
from .task_handler import HandlerRegistry
from .node import Node

class Renderer:
    pipeline = HandlerRegistry(label="on_render")

    @pipeline.register(caller_cls=Node)
    @staticmethod
    def _render_content_tmpl(entity: Node, ctx: ContextView) -> ContentFragment:
        return ContentFragment( content=entity.content_tmpl )
    # or should we use content tmpl to aggregate all the individual components into content fragments?
    # do we always return a list?  A node might result in a bunch of dialog fragments

    @classmethod
    def render(cls, node, ctx) -> list[ContentFragment]:
        return cls.pipeline.execute_all(entity=node, ctx=ctx) or []
