from tangl33.core import Fragment
from ...journal import ContentFragment
from ..enums import ServiceKind
from ..handler import Handler
from ..gather import gather_handlers

class RenderHandler(Handler[list[ContentFragment]]):

    def render_fragments(self, caller, ctx) -> list[ContentFragment]:
        return self.func(caller, ctx)

def render_fragments(caller, *scopes, ctx) -> list[ContentFragment]:

    fragments = []
    for h in gather_handlers(ServiceKind.RENDER, caller, *scopes, ctx=ctx):
        fragments.extend(h.render_fragments(caller, ctx))
    return fragments
