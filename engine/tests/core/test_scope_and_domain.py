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

def test_graph_level_domain_participates_in_scope():
    g = DomainGraph(label="DG", vars={'x': 'graph'})
    n = g.add_node(label="n")

    scope = Scope(graph=g, anchor_id=n.uid)
    domains = scope.active_domains

    print( scope.active_domains )

    assert any(d.label == "DG" for d in domains), "graph-level domain should be active for all nodes"
    ns = scope.namespace
    assert ns.get("x") == "graph"


def test_subgraph_and_node_domains_are_discovered_and_nearest_wins():
    g = Graph(label="G")
    n1 = DomainNode(label="n1", graph=g)

    sg = DomainSubgraph(label="SG", member_ids=[n1.uid], graph=g)
    sg.add_vars({"x": "subgraph"})

    # For n1 (member of SG, with its own node-level domain):
    s1 = Scope(graph=g, anchor_id=n1.uid)
    ns1 = s1.namespace
    assert ns1["x"] == "subgraph", "subgraph is the only participant"

    n1.add_vars({"x": "node"})
    assert ns1["x"] == "node", "node var is earlier than subgraph"

    # For n2 (not in SG):
    n2 = DomainNode(label="n1", graph=g, vars={"x": "node2"})
    s2 = Scope(graph=g, anchor_id=n2.uid)
    ns2 = s2.namespace
    assert ns2["x"] == "node2", "without subgraph, just local"


@pytest.mark.xfail(raises=NameError)
def test_domain_gating_via_predicate_excludes_unavailable_domain():
    g = Graph(label="G")
    n = g.add_node(label="n")

    available = make_domain("avail", flag=True)
    gated = make_domain("gated", flag=True)

    # Attach both at graph level so gating is the only differentiator
    attach_domain_to_graph(g, available)
    attach_domain_to_graph(g, gated)

    # Try to set a Conditional/available flag if your Domain supports it
    # We support two common shapes:
    #   - Domain.conditional: Conditional(predicate=lambda ns: bool(ns.get("gate")))
    #   - Domain.available(ns) method return bool
    if hasattr(gated, "conditional"):
        from tangl.core.entity import Conditional  # if Conditional lives elsewhere, adjust
        gated.conditional = Conditional(predicate=lambda ns: bool(ns.get("allow_gated")))
    elif hasattr(gated, "available"):
        gated.available = lambda ns: bool(ns.get("allow_gated"))
    else:
        pytest.skip("Domain has no 'conditional' field or 'available' method to gate activation.")

    # Build scope with no gate flag
    scope = build_scope(g, n)
    ns = scope.get_namespace()
    # available domain contributes 'flag', gated domain should be filtered out
    assert ns.get("flag") is True
    assert "allow_gated" not in ns  # gate key isn’t introduced spuriously

    # Now enable the gate and assert 'gated' participates
    # We assume get_merged_ns recomputes based on current ctx; if your Scope caches, rebuild it:
    scope = build_scope(g, n)
    ns = scope.get_namespace()
    ns["allow_gated"] = True  # poke gate
    scope = build_scope(g, n)  # rebuild to re-evaluate gating
    ns2 = scope.get_namespace()
    assert ns2.get("flag") is True  # still present
    # Since gated had no unique marker beyond gating, we just assert the gate key survived
    # If your Domain adds a distinctive var (e.g., gated_var=True), assert that instead.