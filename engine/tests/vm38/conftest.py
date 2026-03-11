"""Shared fixtures and helpers for vm38 tests.

Provides graph-building utilities, dispatch isolation, and lightweight
context objects that satisfy the BehaviorRegistry protocol without
requiring the full Ledger/Frame stack.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import Field

from tangl.core import (
    BehaviorRegistry,
    DispatchLayer,
    Entity,
    Graph,
    Node,
    OrderedRegistry,
    Record,
    Selector,
)
from tangl.vm.dispatch import dispatch as vm_dispatch
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge


# ============================================================================
# Test record types
# ============================================================================


class SimpleFragment(Record):
    """Lightweight fragment for journal output assertions."""

    content: str = ""


# ============================================================================
# Dispatch isolation
# ============================================================================


@pytest.fixture(autouse=True)
def clean_vm_dispatch():
    """Isolate vm_dispatch mutations while preserving pre-registered handlers.

    Some non-vm38 modules (for example story runtime handlers) register vm hooks
    at import time during test collection. vm38 tests should run against a clean
    registry, but must not permanently remove those baseline registrations for
    subsequent modules in the same pytest session.
    """
    baseline_behaviors = list(vm_dispatch.values())
    vm_dispatch.clear()
    try:
        yield
    finally:
        vm_dispatch.clear()
        for behavior in baseline_behaviors:
            vm_dispatch.add(behavior)


# ============================================================================
# Context helpers
# ============================================================================


@pytest.fixture
def null_ctx() -> SimpleNamespace:
    """Minimal context satisfying the dispatch protocol.

    Has ``get_authorities()`` and ``get_inline_behaviors()`` — enough for
    ``do_*`` functions to run without error when no handlers are registered.
    """
    return SimpleNamespace(
        get_authorities=lambda: [],
        get_inline_behaviors=lambda: [],
    )


@pytest.fixture
def ctx_with_vm_dispatch() -> SimpleNamespace:
    """Context that includes the module-level vm_dispatch registry.

    Use when you need system handlers to fire through ``do_*`` functions.
    """
    return SimpleNamespace(
        get_authorities=lambda: [vm_dispatch],
        get_inline_behaviors=lambda: [],
    )


@pytest.fixture
def ctx_factory():
    """Build a context with custom registries and/or inline behaviors."""

    def _make(registries=None, inline=None):
        return SimpleNamespace(
            get_authorities=lambda: list(registries or []),
            get_inline_behaviors=lambda: list(inline or []),
        )

    return _make


# ============================================================================
# Graph building helpers
# ============================================================================


@pytest.fixture
def graph() -> Graph:
    """Fresh empty graph."""
    return Graph()


def make_linear_graph(labels: list[str], *, graph: Graph | None = None) -> tuple[Graph, list[TraversableNode]]:
    """Build a linear chain of TraversableNodes with edges between them.

    Returns ``(graph, [node_a, node_b, ...])``.  Edges are persistent
    ``TraversableEdge`` instances.
    """
    g = graph or Graph()
    nodes = [_node(g, label=lbl) for lbl in labels]
    for i in range(len(nodes) - 1):
        _edge(g, predecessor_id=nodes[i].uid,
            successor_id=nodes[i + 1].uid,
        )
    return g, nodes


def make_branching_graph(
    root_label: str = "root",
    branch_labels: list[list[str]] | None = None,
    *,
    graph: Graph | None = None,
) -> tuple[Graph, TraversableNode, list[list[TraversableNode]]]:
    """Build a root node with multiple branches.

    Returns ``(graph, root, [[branch0_nodes], [branch1_nodes], ...])``.
    """
    g = graph or Graph()
    root = _node(g, label=root_label)
    branches: list[list[TraversableNode]] = []

    for branch in branch_labels or [["b0a", "b0b"], ["b1a", "b1b"]]:
        nodes = [_node(g, label=lbl) for lbl in branch]
        _edge(g, predecessor_id=root.uid,
            successor_id=nodes[0].uid,
        )
        for i in range(len(nodes) - 1):
            _edge(g, predecessor_id=nodes[i].uid,
                successor_id=nodes[i + 1].uid,
            )
        branches.append(nodes)

    return g, root, branches


def make_container(
    container_label: str,
    member_labels: list[str],
    *,
    graph: Graph | None = None,
) -> tuple[Graph, TraversableNode, list[TraversableNode]]:
    """Build a container with child members and internal edges.

    The first member is designated as the source (entry point).
    The last member is designated as the sink (exit point).
    Internal edges connect members linearly.

    Returns ``(graph, container, [member0, member1, ...])``.
    """
    g = graph or Graph()
    container = _node(g, label=container_label)
    members = [_node(g, label=lbl) for lbl in member_labels]

    for m in members:
        container.add_child(m)

    if members:
        container.source_id = members[0].uid
    if len(members) > 1:
        container.sink_id = members[-1].uid
        for i in range(len(members) - 1):
            _edge(g, predecessor_id=members[i].uid,
                successor_id=members[i + 1].uid,
            )

    return g, container, members
