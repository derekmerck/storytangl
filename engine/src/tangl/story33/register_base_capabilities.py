# setup basic handlers and providers
from tangl33.core.type_hints import StringMap
from tangl33.core import context_cap, render_cap, effect_cap, redirect_cap, continue_cap, EdgeKind, Edge, ChoiceTrigger, Node, Graph, Domain

from .renderers import render_text, render_choices
from ..core.scope import GlobalScope


@continue_cap()
def auto_continue(node: Node, driver, graph: Graph, ctx: StringMap):
    # auto-advance if exactly one CHOICE edge
    choices = [e for e in graph.edges_out.get(node.uid, [])
               if e.kind is EdgeKind and e.trigger is ChoiceTrigger.AFTER]
    return choices[0] if len(choices) == 1 else None

def register_base_capabilities():
    GlobalScope.get_instance().add_handler("render", render_text)
    GlobalScope.get_instance().add_handler("render", render_choices)
    GlobalScope.get_instance().add_handler("choice", auto_continue)
