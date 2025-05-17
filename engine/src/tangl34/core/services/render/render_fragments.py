from ...journal import ContentFragment
from ..enums import ServiceKind
from ..gather import gather_handlers


def render_fragments(*scopes, ctx) -> list[ContentFragment]:

    node, graph, *scopes = scopes

    fragments = []
    for h in gather_handlers(ServiceKind.RENDER, *scopes):
        fragments.extend(h.render_fragments(ctx))
    return fragments
