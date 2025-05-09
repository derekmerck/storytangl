import pytest
from collections import ChainMap

from tangl33.core.enums import Tier
from tangl33.core.graph.node import Node
from tangl33.core.graph.graph import Graph
from tangl33.core.runtime.handler_cache import HandlerCache
from tangl33.core.context.gather import gather
from tangl33.core.type_hints import Context

# -----------------------------------------------------------------------------
# Context gather + iter_ancestors behaviour
# -----------------------------------------------------------------------------
def test_iter_ancestors_order(graph):
    child = graph.find_one(label="child")
    root  = graph.find_one(label="root")
    anc = [n.label for n in child.iter_ancestors(graph=graph)]
    assert anc == [root.label], "iter_ancestors should return root first-to-last"

def test_gather_merges_layers(graph, cap_cache):
    root = graph.find_one(label="root")
    child = graph.find_one(label="child")

    # register two dummy context providers, one at each tier
    from tangl33.core.context.context_handler import ContextHandler
    cap_cache.register(
        ContextHandler(lambda *_: {"root_var": 1}, tier=Tier.NODE, owner_uid=root.uid)
    )
    cap_cache.register(
        ContextHandler(lambda *_: {"child_var": 2}, tier=Tier.NODE, owner_uid=child.uid)
    )

    ctx: Context = gather(child, graph, cap_cache, globals={})
    assert isinstance(ctx, ChainMap)
    assert ctx["root_var"] == 1 and ctx["child_var"] == 2
    # child values overshadow ancestor on key clash
    cap_cache.register(
        ContextHandler(lambda *_: {"dup": "root"}, tier=Tier.NODE, owner_uid=root.uid)
    )
    cap_cache.register(
        ContextHandler(lambda *_: {"dup": "child"}, tier=Tier.NODE, owner_uid=child.uid)
    )
    ctx = gather(child, graph, cap_cache, globals={})
    assert ctx["dup"] == "child"
