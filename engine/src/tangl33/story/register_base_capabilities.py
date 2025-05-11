# setup basic handlers and providers
from tangl33.core.context.context_cap import context_cap
from tangl33.core.render.render_cap   import render_cap
from tangl33.core.cursor.step_caps    import (
    redirect_cap, continue_cap, effect_cap
)
from tangl33.core.render.fragment import Fragment
from tangl33.core.graph.edge import EdgeKind, Edge, EdgeTrigger

from .renderers import render_text, render_choices

@continue_cap()
def auto_continue(node, driver, graph, ctx):
    # auto-advance if exactly one CHOICE edge
    choices = [e for e in graph.edges_out.get(node.uid, [])
               if e.kind is EdgeKind and e.trigger is EdgeTrigger.AFTER]
    return choices[0] if len(choices) == 1 else None

def register_base_capabilities(cap_cache):
    cap_cache.register(auto_continue)
    cap_cache.register(render_text)
    # cap_cache.register(render_choices)

