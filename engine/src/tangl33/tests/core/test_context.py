import pytest
from collections import ChainMap

from tangl33.core import Tier, TierView
from tangl33.core.type_hints import StringMap
from tangl33.core.context.gather_context import gather_context

# -----------------------------------------------------------------------------
# StringMap gather + iter_ancestors behaviour
# -----------------------------------------------------------------------------
def test_iter_ancestors_order(graph):
    child = graph.find_one(label="child")
    root  = graph.find_one(label="root")
    anc = [n.label for n in child.iter_ancestors(graph=graph)]
    assert anc == [root.label], "iter_ancestors should return root first-to-last"

@pytest.mark.skip(reason="deprecated")
def test_gather_merges_layers(graph, cap_cache):
    root = graph.find_one(label="root")
    child = graph.find_one(label="child")

    # register two dummy context providers, one at each tier
    from tangl33.core.context.context_cap import ContextCap
    cap_cache.register(
        ContextCap(lambda *_: {"root_var": 1}, tier=Tier.NODE, owner_uid=root.uid)
    )
    cap_cache.register(
        ContextCap(lambda *_: {"child_var": 2}, tier=Tier.NODE, owner_uid=child.uid)
    )

    ctx: StringMap = gather_context(child, graph, cap_cache, globals={})
    assert isinstance(ctx, ChainMap)  # Actually a TieredContextMap subclass of chainmap
    assert isinstance(ctx, TierView)
    assert ctx["root_var"] == 1 and ctx["child_var"] == 2
    # child values overshadow ancestor on key clash
    cap_cache.register(
        ContextCap(lambda *_: {"dup": "root"}, tier=Tier.NODE, owner_uid=root.uid)
    )
    cap_cache.register(
        ContextCap(lambda *_: {"dup": "child"}, tier=Tier.NODE, owner_uid=child.uid)
    )
    ctx = gather_context(child, graph, cap_cache, globals={})
    assert ctx["dup"] == "child"

def test_gather_overrides():
    from tangl33.core import Node, Graph, Domain
    graph = Graph()
    node = Node(label="node", locals={'a': 1}); graph.add(node)
    root = Node(label="root", locals={'a': 2, 'b': 3}); graph.add(root)
    node.parent_uid = root.uid
    ctx = gather_context(node, graph, Domain())
    assert ctx == {"a": 1, "b": 3}