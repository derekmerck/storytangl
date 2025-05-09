from tangl33.core import EdgeKind, render_handler, Fragment

@render_handler()
def render_text(node, driver, graph, ctx):
    """Render a basic text fragment from node content."""
    if 'text' in node.locals:
        return Fragment(node_uid=node.uid, text=node.locals['text'])

@render_handler()
def render_choices(node, driver, graph, ctx):
    """Render available choices from outgoing edges."""
    choices = []
    for edge in graph.edges_out.get(node.uid, []):
        if edge.kind == EdgeKind.CHOICE:
            # Create a fragment for this choice
            text = edge.data.get('text', f"Go to {graph.get(edge.dst_uid).label}")
            choices.append(Fragment(node_uid=node.uid, text=text))
    return choices
