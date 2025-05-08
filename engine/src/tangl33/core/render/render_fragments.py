from ..type_hints import Context
from ..graph import Node
from .fragment import Fragment

def render_fragments(node: Node, ctx: Context) -> list[Fragment]:
    ...
    # uses cap_cache.iter_phase(RENDER, …).