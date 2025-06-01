import logging

from tangl.core import EdgeKind, render_cap, Fragment

logger = logging.getLogger(__name__)

from jinja2 import Environment

def render_str(s: str, **ctx):
    j2tmpl = Environment().from_string(s)
    logger.debug( list(ctx.keys()) )
    return j2tmpl.render(ctx)

@render_cap()
def render_text(node, driver, graph, ctx):
    """Render a basic text fragment from node content."""
    logger.debug(f'Rendering text fragment from node {node!r}')
    if 'text' in node.locals:
        s = render_str(node.locals['text'], **ctx)
        return Fragment(node_uid=node.uid, text=s)

@render_cap()
def render_choices(node, driver, graph, ctx):
    """Render available choices from outgoing edges."""
    choices = []
    for edge in graph.edges_out.get(node.uid, []):
        if edge.kind == EdgeKind.CHOICE:
            # Create a fragment for this choice
            text = edge.data.get('text', f"Go to {graph.get(edge.dst_uid).label}")
            choices.append(Fragment(node_uid=node.uid, text=text))
    return choices
