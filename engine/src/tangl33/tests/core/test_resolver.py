"""
Extended core tests: provision index, resolver, context gather & iter_ancestors.
Run: pytest -q
"""
from uuid import uuid4
import pytest
from collections import ChainMap

from tangl33.core.enums import Phase, Tier
from tangl33.core.graph.edge import EdgeKind
from tangl33.core.graph.node import Node
from tangl33.core.graph.graph import Graph
from tangl33.core.runtime.handler_cache import HandlerCache
from tangl33.core.runtime.provider_registry import ProviderRegistry
from tangl33.core.provision.provider_cap import ProviderCap
from tangl33.core.requirement import Requirement
from tangl33.core.context.gather import gather
from tangl33.core.resolver.resolve import resolve
from tangl33.core.type_hints import StringMap

# -----------------------------------------------------------------------------
# ProvisionRegistry & resolver basics
# -----------------------------------------------------------------------------
def test_provision_registry_lookup(prov_reg):
    cap = ProviderCap(
        owner_uid=uuid4(),
        provides={"shop"},
        tier=Tier.GRAPH,
    )
    prov_reg.add(cap)
    found = list(prov_reg.providers("shop", Tier.GRAPH))
    assert found == [cap]

def test_resolver_creates_link(graph, prov_reg, cap_cache):
    shop_node = Node(label="shop")
    shop_cap  = ProviderCap(
        owner_uid=shop_node.uid,
        provides={"shop"},
        tier=Tier.GRAPH,
    )
    prov_reg.add(shop_cap)
    graph.add(shop_node)

    req_node = graph.find_one(label="child")
    req_node.requires = {Requirement("shop")}
    resolve(req_node, graph, prov_reg, cap_cache, ctx={})

    # after resolve we should have an outgoing "satisfies" edge
    assert any(
        e.dst_uid == shop_node.uid and e.kind is EdgeKind.PROVIDES
        for e in graph.edges_out[req_node.uid]
    )
