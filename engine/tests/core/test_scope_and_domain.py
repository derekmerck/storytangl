"""
These tests assert that Scope discovers domains attached at graph/subgraph/node,
and that namespace merging respects a nearest-wins precedence.
"""

import pytest

from tangl.core import Graph, Domain, Scope, global_domain
from tangl.core.domain import DomainSubgraph, AffiliateDomain, DomainNode, DomainGraph


def test_global_domain_is_present_in_scope_smoke():
    g = Graph(label="G")
    n = g.add_node(label="n")
    s = Scope(graph=g, anchor_id=n.uid)
    # Try to detect by label or by a conventional var
    active = s.active_domains
    assert active is not None, "Scope should expose active domains"

    labels = {getattr(d, "label", None) for d in active}
    assert global_domain.label in labels, "global domain should always in scope"


# --- tests ----------------------------------------------------------------

@pytest.mark.xfail(reason="deprecated, this should be part of application domain tests?")
def test_graph_level_domain_participates_in_scope():
    g = DomainGraph(label="DG", locals={'x': 'graph'})
    n = g.add_node(label="n")

    scope = Scope(graph=g, anchor_id=n.uid)
    domains = scope.active_domains

    print( scope.active_domains )

    assert any(d.label == "DG" for d in domains), "graph-level domain should be active for all nodes"
    from tangl.vm.vm_dispatch.on_get_ns import do_get_ns
    ns = do_get_ns(scope)
    assert ns.get("x") == "graph"

@pytest.mark.xfail(reason="deprecated, domains going away")
def test_subgraph_and_node_domains_are_discovered_and_nearest_wins():
    g = Graph(label="G")
    n1 = DomainNode(label="n1", graph=g)

    sg = DomainSubgraph(label="SG", member_ids=[n1.uid], graph=g)
    sg.locals['x'] = "subgraph"

    # For n1 (member of SG, with its own node-level domain):
    s1 = Scope(graph=g, anchor_id=n1.uid)

    from tangl.vm.context import Context
    ns1 = Context._get_ns(s1)
    # ns1 = s1.namespace
    assert ns1["x"] == "subgraph", "subgraph is the only participant"

    n1.locals['x'] = "node"
    ns1 = Context._get_ns(s1)
    assert ns1["x"] == "node", "node var is earlier than subgraph"

    # For n2 (not in SG):
    n2 = DomainNode(label="n1", graph=g, locals={"x": "node2"})
    s2 = Scope(graph=g, anchor_id=n2.uid)

    ns2 = Context._get_ns(s2)
    # ns2 = s2.namespace
    assert ns2["x"] == "node2", "without subgraph, just local"
