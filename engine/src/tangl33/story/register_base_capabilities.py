# setup basic handlers and providers
from tangl33.core.context.context_handler import context_handler
from tangl33.core.render.render_handler   import render_handler
from tangl33.core.cursor.step_handlers    import (
    redirect_handler, continue_handler, effect_handler
)
from tangl33.core.render.fragment import Fragment
from tangl33.core.graph.edge import EdgeKind, Edge, ChoiceTrigger

from .renderers import render_text, render_choices

# @render_handler()                     # Phase.RENDER @ Tier.NODE
# def render_text(node, *_):
#     if "text" in node.locals:
#         return Fragment(text=node.locals["text"], node_uid=node.uid)

@continue_handler()
def auto_continue(node, driver, graph, ctx):
    # auto-advance if exactly one CHOICE edge
    choices = [e for e in graph.edges_out.get(node.uid, [])
               if e.kind is EdgeKind and e.trigger is ChoiceTrigger.AFTER]
    return choices[0] if len(choices) == 1 else None

def register_base_capabilities(cap_cache):
    cap_cache.register(auto_continue)
    cap_cache.register(render_text)
    # cap_cache.register(render_choices)

