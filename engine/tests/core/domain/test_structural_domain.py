from __future__ import annotations

from tangl.core.graph import Graph
from tangl.core.domain import DomainNode


def test_domain_node_add_and_remove_child_wires_membership_and_edge():
    graph = Graph(label="graph")
    parent = DomainNode(label="parent", graph=graph)
    child_a = DomainNode(label="child-a", graph=graph)
    child_b = DomainNode(label="child-b", graph=graph)

    parent.add_child(child_a)
    parent.add_child(child_b)

    children = list(parent.children())
    assert child_a in children
    assert child_b in children
    assert parent.has_member(child_a)
    assert parent.has_member(child_b)

    edge = graph.find_edge(source=parent, destination=child_a, edge_type="child")
    assert edge is not None
    assert edge.source is parent
    assert edge.destination is child_a

    parent.remove_child(child_a)

    assert parent.has_member(child_a) is False
    assert child_a not in list(parent.children())
    assert graph.find_edge(source=parent, destination=child_a, edge_type="child") is None
    assert parent.has_member(child_b)


def test_domain_node_find_helpers_filter_children_by_criteria():
    graph = Graph(label="graph")
    parent = DomainNode(label="parent", graph=graph)

    alpha = DomainNode(label="alpha", graph=graph, tags={"shared"})
    beta = DomainNode(label="beta", graph=graph, tags={"shared", "beta"})
    gamma = DomainNode(label="gamma", graph=graph)

    parent.add_child(alpha)
    parent.add_child(beta)
    parent.add_child(gamma)

    shared_children = list(parent.find_children(has_tags={"shared"}))
    assert shared_children == [alpha, beta]

    assert parent.find_child(label="beta") is beta
    assert parent.find_child(label="missing") is None


def test_domain_node_reparenting_is_exclusive_and_invalidation_occurs():
    graph = Graph(label="graph")
    parent_a = DomainNode(label="parent-a", graph=graph)
    parent_b = DomainNode(label="parent-b", graph=graph)
    child = DomainNode(label="child", graph=graph)

    parent_a.add_child(child)
    assert child.parent is parent_a

    # Cache the parent property then reparent to ensure invalidation occurs.
    cached_parent = child.parent
    assert cached_parent is parent_a

    parent_b.add_child(child)

    assert child.parent is parent_b
    assert child not in list(parent_a.children())
    assert parent_a.has_member(child) is False
    assert parent_b.has_member(child) is True

    edges_to_child = list(graph.find_edges(source=parent_b, destination=child, edge_type="child"))
    assert len(edges_to_child) == 1
    assert graph.find_edge(source=parent_a, destination=child, edge_type="child") is None

    # Adding the same child again should be idempotent.
    parent_b.add_child(child)
    edges_after = list(graph.find_edges(source=parent_b, destination=child, edge_type="child"))
    assert len(edges_after) == 1
