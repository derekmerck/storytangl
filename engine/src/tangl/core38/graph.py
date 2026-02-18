# tangl/core/graph.py
"""Graph topology primitives.

This module consolidates the v38 graph surface (nodes, edges, subgraphs, and
hierarchical nodes) into one file. It focuses on topology shape and typed queries;
VM/service layers provide traversal policy and execution behavior.

See Also
--------
:mod:`tangl.core38.registry`
    Graph extends :class:`Registry` and reuses registry-aware/group primitives.
:mod:`tangl.vm.frame`
    Runtime traversal and cursor behavior is layered above core topology.
"""

from __future__ import annotations

import itertools
from typing import Iterable, Iterator, Optional
from uuid import UUID

from .entity import Entity
from .registry import EntityGroup, HierarchicalGroup, Registry, RegistryAware
from .selector import Selector


class GraphItem(RegistryAware):
    """Base class for items managed by :class:`Graph`.

    Graph items are registry-aware entities. ``graph`` is the preferred alias for the
    bound registry pointer when the owner is a graph.
    """

    @property
    def graph(self) -> Graph:
        return self._registry


class Graph(Registry[GraphItem]):
    """Specialized registry for graph topology.

    Why
    ---
    Graph centralizes topology shape concerns:

    - typed creation helpers for nodes/edges/subgraphs,
    - typed selector-based queries,
    - and graph-level hook bridges for link/unlink operations.

    Notes
    -----
    Creation helpers instantiate ``kind(**attrs)`` directly, then rely on registry
    ownership for binding and lifecycle hooks.

    Typed find helpers apply narrowing via ``selector.with_criteria(has_kind=...)``.
    Because ``with_criteria`` avoids widening ``has_kind``, callers may narrow kinds
    but cannot widen helper defaults.

    Example:
        >>> g = Graph()
        >>> a = Node(label="a", registry=g)
        >>> b = Node(label="b", registry=g)
        >>> e = g.add_edge(a, b, label="ab")
        >>> g.nodes
        [<Node:a>, <Node:b>]
        >>> e.predecessor is a and e.successor is b
        True
    """

    def get_authorities(self) -> list[object]:
        """Return optional application-level behavior registries.

        Notes
        -----
        This hook is intentionally minimal and provisional. Authorities are
        primarily an application/story concern (for example a story graph may
        return story/world registries). Core exposes this no-op hook so runtime
        layers can discover authorities via protocol (`if hook exists`) without
        type-coupling to higher-order graph types.
        """
        return []

    def add_node(self, *, kind=None, **attrs) -> Node:
        """Create and add a node-like graph item."""
        kind = kind or Node
        node = kind(**attrs)
        self.add(node)
        return node

    def add_edge(
        self,
        predecessor: GraphItem,
        successor: GraphItem,
        *,
        kind=None,
        **attrs,
    ) -> Edge:
        """Create and add an edge between predecessor and successor items."""
        if predecessor is not None:
            self._validate_linkable(predecessor)
            predecessor_id = predecessor.uid
        else:
            predecessor_id = None

        if successor is not None:
            self._validate_linkable(successor)
            successor_id = successor.uid
        else:
            successor_id = None

        kind = kind or Edge
        edge = kind(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            **attrs,
        )
        self.add(edge)
        return edge

    def add_subgraph(self, *, kind=None, members: Iterable[GraphItem] = None, **attrs) -> Subgraph:
        """Create and add a subgraph, then optionally add members."""
        kind = kind or Subgraph
        subgraph = kind(**attrs)
        self.add(subgraph)
        for item in members or ():
            subgraph.add_member(item)
        return subgraph

    def find_subgraphs(self, selector: Selector = Selector()) -> Iterator[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_all(selector)

    def find_subgraph(self, selector: Selector = Selector()) -> Optional[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_one(selector)

    @property
    def subgraphs(self) -> list[Subgraph]:
        return list(self.find_subgraphs())

    def find_edges(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_all(selector)

    @property
    def edges(self) -> list[Edge]:
        return list(self.find_edges())

    def find_edge(self, selector: Selector = Selector()) -> Optional[Edge]:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_one(selector)

    def find_nodes(self, selector: Selector = Selector()) -> Iterator[Node]:
        selector = selector.with_criteria(has_kind=Node)
        return self.find_all(selector)

    @property
    def nodes(self) -> list[Node]:
        return list(self.find_nodes())

    def find_node(self, selector: Selector = Selector()) -> Optional[Node]:
        selector = selector.with_criteria(has_kind=Node)
        return self.find_one(selector)

    def _do_link(self, caller: GraphItem, node: Node, _ctx):
        """Bridge to dispatch ``do_link`` hook."""
        from .dispatch import do_link

        return do_link(caller=caller, node=node, ctx=_ctx)

    def _do_unlink(self, caller: GraphItem, node: Node, _ctx):
        """Bridge to dispatch ``do_unlink`` hook."""
        from .dispatch import do_unlink

        return do_unlink(caller=caller, node=node, ctx=_ctx)


class Subgraph(EntityGroup, GraphItem):
    """Non-hierarchical grouping of graph items.

    Subgraph reuses :class:`EntityGroup` membership semantics and adds graph-level
    link/unlink hook bridge calls when context is provided.
    """

    def add_member(self, item: GraphItem, _ctx=None) -> None:
        self.graph._validate_linkable(item)
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            self.graph._do_link(self, item, _ctx)
        super().add_member(item)

    def remove_member(self, item: GraphItem, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            self.graph._do_unlink(self, item, _ctx)
        super().remove_member(item)

    def members(self, selector: Selector = None, sort_key=None) -> Iterator[GraphItem]:
        """Yield typed graph-item members."""
        return super().members(selector=selector, sort_key=sort_key)


class Edge(GraphItem):
    """Directed connection between predecessor and successor graph items.

    Notes
    -----
    - v38 names endpoints ``predecessor`` / ``successor`` (legacy used
      ``source`` / ``destination``).
    - Endpoints may be dangling (`None`) by design.

    Access patterns:
    - ``edge.predecessor`` / ``edge.successor`` for graph-dereferenced properties.
    - ``edge.set_predecessor(node, _ctx=...)`` for explicit context-driven mutation.
    - ``edge.predecessor = node`` for ambient-context mutation only.

    Example:
        >>> g = Graph()
        >>> n = Node(label="n", registry=g)
        >>> e = Edge(registry=g, successor_id=n.uid)
        >>> g.find_one(Selector(successor=n))
        <Edge:anon->n>
    """

    predecessor_id: Optional[UUID] = None
    successor_id: Optional[UUID] = None

    @property
    def predecessor(self) -> Optional[Node]:
        return self.graph.get(self.predecessor_id)

    def set_predecessor(self, value: Node, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if value is not None:
            self.graph._validate_linkable(value)
            if _ctx is not None:
                self.graph._do_link(self, value, _ctx)
            self.predecessor_id = value.uid
        else:
            if _ctx is not None and self.predecessor is not None:
                self.graph._do_unlink(self, self.predecessor, _ctx)
            self.predecessor_id = None

    @predecessor.setter
    def predecessor(self, value: Node) -> None:
        self.set_predecessor(value)

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id)

    def set_successor(self, value: Node, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if value is not None:
            self.graph._validate_linkable(value)
            if _ctx is not None:
                self.graph._do_link(self, value, _ctx)
            self.successor_id = value.uid
        else:
            if _ctx is not None and self.successor is not None:
                self.graph._do_unlink(self, self.successor, _ctx)
            self.successor_id = None

    @successor.setter
    def successor(self, value: Node) -> None:
        self.set_successor(value)

    def __repr__(self) -> str:
        src = self.predecessor.get_label() if self.predecessor is not None else "anon"
        dst = self.successor.get_label() if self.successor is not None else "anon"
        return f"<{self.__class__.__name__}:{src[:6]}->{dst[:6]}>"


class Node(GraphItem):
    """Graph vertex with directional edge navigation and wiring helpers."""

    def edges_in(self, selector: Selector = None) -> Iterator[Edge]:
        selector = (selector or Selector()).with_criteria(successor=self)
        return self.graph.find_edges(selector)

    def predecessors(self, selector: Selector = None) -> Iterator[Node]:
        """Yield immediate predecessor nodes via incoming edges."""
        return (edge.predecessor for edge in self.edges_in(selector) if edge.predecessor)

    def edges_out(self, selector: Selector = None) -> Iterator[Edge]:
        selector = (selector or Selector()).with_criteria(predecessor=self)
        return self.graph.find_edges(selector)

    def successors(self, selector: Selector = None) -> Iterator[Node]:
        """Yield immediate successor nodes via outgoing edges."""
        return (edge.successor for edge in self.edges_out(selector) if edge.successor)

    def edges(self, selector: Selector = None) -> Iterator[Edge]:
        """Yield all incident edges (incoming then outgoing)."""
        return itertools.chain(self.edges_in(selector), self.edges_out(selector))

    def add_edge_to(self, node: Node, kind=None, **attrs) -> Edge:
        """Create an edge from this node to ``node``."""
        return self.graph.add_edge(self, node, kind=kind, **attrs)

    def add_edge_from(self, node: Node, kind=None, **attrs) -> Edge:
        """Create an edge from ``node`` to this node."""
        return self.graph.add_edge(node, self, kind=kind, **attrs)

    def remove_edge_to(self, node: Node) -> None:
        edge = self.graph.find_edge(Selector(predecessor=self, successor=node))
        if edge is not None:
            self.graph.remove(edge.uid)

    def remove_edge_from(self, node: Node) -> None:
        edge = self.graph.find_edge(Selector(predecessor=node, successor=self))
        if edge is not None:
            self.graph.remove(edge.uid)


class HierarchicalNode(HierarchicalGroup, Node):
    """Node + hierarchy composition.

    This class combines :class:`HierarchicalGroup` (parent/path/ancestor semantics)
    with :class:`Node` (edge navigation and wiring helpers).
    """
