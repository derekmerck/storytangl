# tangl/core/graph.py
"""Graph topology primitives.

This module consolidates the v38 graph surface (nodes, edges, subgraphs, and
hierarchical nodes) into one file. It focuses on topology shape and typed queries;
VM/service layers provide traversal policy and execution behavior.

See Also
--------
:mod:`tangl.core.registry`
    Graph extends :class:`Registry` and reuses registry-aware/group primitives.
:mod:`tangl.vm.frame`
    Runtime traversal and cursor behavior is layered above core topology.
"""

from __future__ import annotations

import itertools
from fnmatch import fnmatch
from typing import Any, Iterable, Iterator, Optional
from uuid import UUID

from pydantic import AliasChoices, Field

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

    @graph.setter
    def graph(self, value: Graph | None) -> None:
        # Compatibility for legacy graph containers that assign item.graph directly.
        self.bind_registry(value)

    def _compat_parent(self) -> GraphItem | None:
        parent = getattr(self, "parent", None)
        if parent is not None:
            return parent
        registry = getattr(self, "registry", None)
        if registry is None:
            return None
        for candidate in registry.find_all(Selector(has_member=self)):
            if candidate is not self:
                return candidate
        return None

    def ancestors(self):
        """Legacy compatibility iterator from parent to root.

        Falls back to membership-derived ancestry when no hierarchical
        ``parent`` is available (for example, plain Subgraph membership).
        """
        seen: set[UUID | None] = {getattr(self, "uid", None)}
        current: GraphItem | None = self
        while current is not None:
            parent = current._compat_parent()
            if parent is None:
                return
            uid = getattr(parent, "uid", None)
            if uid in seen:
                return
            seen.add(uid)
            yield parent
            current = parent

    def has_path(self, pattern: str) -> bool:
        """Legacy compatibility predicate for selector ``has_path`` criteria."""
        path = getattr(self, "path", None)
        if not isinstance(path, str):
            labels: list[str] = [self.get_label()]
            for ancestor in self.ancestors():
                labels.append(ancestor.get_label())
            path = ".".join(reversed(labels))
        return fnmatch(path, pattern)

    def has_ancestor_tags(self, tags: set[str]) -> bool:
        """Legacy compatibility predicate for selector ``has_ancestor_tags``."""
        if not tags:
            return True
        wanted = set(tags)
        pooled: set[str] = set()
        pooled.update(getattr(self, "tags", set()) or set())
        for ancestor in self.ancestors():
            pooled.update(getattr(ancestor, "tags", set()) or set())
        return wanted.issubset(pooled)

    def has_ancestor_tags__not(self, tags: set[str]) -> bool:
        """Legacy compatibility negative scope predicate."""
        if not tags:
            return True
        forbidden = set(tags)
        pooled: set[str] = set()
        pooled.update(getattr(self, "tags", set()) or set())
        for ancestor in self.ancestors():
            pooled.update(getattr(ancestor, "tags", set()) or set())
        return forbidden.isdisjoint(pooled)


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
        """Return application-level behavior registries for dispatch bootstrapping.

        Extension hook — override in application-layer graph subclasses to
        expose domain-specific registries to the VM dispatch chain.

        The no-op default is correct for a bare ``Graph``.  Application graphs
        override this to return their registries:

        - :class:`~tangl.story.StoryGraph` returns ``[story_dispatch]``
          and cascades to ``world.get_authorities()`` when a world is attached.
        - Future ``WorldGraph``, ``MechanicsGraph``, etc. follow the same pattern.

        Why a hook on Graph, not a Protocol
        ------------------------------------
        Dispatch bootstrapping cannot use dispatch to assemble itself — the
        authority chain must be discoverable before any hook fires.  A duck-typed
        method on the graph is the right primitive: the VM layer checks
        ``getattr(graph, "get_authorities", None)`` and calls it if present,
        without type-coupling to any application graph class.

        See Also
        --------
        :meth:`tangl.vm.runtime.frame.PhaseCtx.get_authorities`
            Supplies graph/world authority registries to VM dispatch expansion.
        :class:`tangl.story.story_graph.StoryGraph`
            Reference override — returns story and world authority registries.

        Notes
        -----
        The assembly order matters: ``vm_dispatch`` is always first (SYSTEM
        layer), then authorities returned here (APPLICATION and AUTHOR layers)
        in declaration order.  Lower dispatch layers (LOCAL, INLINE) are added
        by ``PhaseCtx.get_authorities`` and inline behavior expansion separately.
        """
        return []

    def add(self, value: GraphItem, _ctx=None) -> None:
        """Add and bind legacy ``graph`` pointers when present."""
        if hasattr(value, "graph"):
            try:
                value.graph = self
            except Exception:
                pass
        super().add(value, _ctx=_ctx)

    def add_node(self, *, kind=None, **attrs) -> Node:
        """Create and add a node-like graph item."""
        if kind is None and "obj_cls" in attrs:
            kind = attrs.pop("obj_cls")
        kind = kind or Node
        node = kind(**attrs)
        self.add(node)
        return node

    def add_edge(
        self,
        predecessor: GraphItem | None = None,
        successor: GraphItem | None = None,
        *,
        kind=None,
        **attrs,
    ) -> Edge:
        """Create and add an edge between predecessor and successor items."""
        if kind is None and "obj_cls" in attrs:
            kind = attrs.pop("obj_cls")
        # Legacy arg aliases.
        if predecessor is None and "source" in attrs:
            predecessor = attrs.pop("source")
        if successor is None and "destination" in attrs:
            successor = attrs.pop("destination")

        # Legacy id aliases when node refs are not supplied.
        predecessor_id = attrs.pop("source_id", None)
        successor_id = attrs.pop("destination_id", None)

        if predecessor is not None:
            self._validate_linkable(predecessor)
            predecessor_id = predecessor.uid

        if successor is not None:
            self._validate_linkable(successor)
            successor_id = successor.uid

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
        if kind is None and "obj_cls" in attrs:
            kind = attrs.pop("obj_cls")
        kind = kind or Subgraph
        subgraph = kind(**attrs)
        self.add(subgraph)
        for item in members or ():
            subgraph.add_member(item)
        return subgraph

    @staticmethod
    def _normalize_edge_criteria(criteria: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(criteria)
        if "source" in normalized and "predecessor" not in normalized:
            normalized["predecessor"] = normalized.pop("source")
        if "destination" in normalized and "successor" not in normalized:
            normalized["successor"] = normalized.pop("destination")
        return normalized

    def _typed_selector(
        self,
        kind: type[GraphItem],
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Selector:
        if issubclass(kind, Edge):
            criteria = self._normalize_edge_criteria(criteria)
        base_selector = self._normalize_selector(selector, **criteria) or Selector()
        return base_selector.with_criteria(has_kind=kind)

    def _find_typed_all(
        self,
        kind: type[GraphItem],
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[GraphItem]:
        return self.find_all(selector=self._typed_selector(kind, selector, **criteria))

    def _find_typed_one(
        self,
        kind: type[GraphItem],
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> GraphItem | None:
        return self.find_one(selector=self._typed_selector(kind, selector, **criteria))

    def find_subgraphs(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Subgraph]:
        return self._find_typed_all(Subgraph, selector, **criteria)

    def find_subgraph(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Optional[Subgraph]:
        return self._find_typed_one(Subgraph, selector, **criteria)

    @property
    def subgraphs(self) -> list[Subgraph]:
        return list(self.find_subgraphs())

    def find_edges(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Edge]:
        return self._find_typed_all(Edge, selector, **criteria)

    @property
    def edges(self) -> list[Edge]:
        return list(self.find_edges())

    def find_edge(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Optional[Edge]:
        return self._find_typed_one(Edge, selector, **criteria)

    def find_nodes(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Node]:
        return self._find_typed_all(Node, selector, **criteria)

    @property
    def nodes(self) -> list[Node]:
        return list(self.find_nodes())

    def find_node(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Optional[Node]:
        return self._find_typed_one(Node, selector, **criteria)

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

    predecessor_id: Optional[UUID] = Field(
        default=None,
        validation_alias=AliasChoices("predecessor_id", "source_id"),
    )
    successor_id: Optional[UUID] = Field(
        default=None,
        validation_alias=AliasChoices("successor_id", "destination_id"),
    )

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

    # Legacy aliases retained for non-retiring call sites.
    @property
    def source(self) -> Optional[Node]:
        return self.predecessor

    def set_source(self, value: Node, _ctx=None) -> None:
        self.set_predecessor(value, _ctx=_ctx)

    @source.setter
    def source(self, value: Node) -> None:
        self.set_predecessor(value)

    @property
    def destination(self) -> Optional[Node]:
        return self.successor

    def set_destination(self, value: Node, _ctx=None) -> None:
        self.set_successor(value, _ctx=_ctx)

    @destination.setter
    def destination(self, value: Node) -> None:
        self.set_successor(value)

    @property
    def source_id(self) -> Optional[UUID]:
        return self.predecessor_id

    @source_id.setter
    def source_id(self, value: UUID | None) -> None:
        self.predecessor_id = value

    @property
    def destination_id(self) -> Optional[UUID]:
        return self.successor_id

    @destination_id.setter
    def destination_id(self, value: UUID | None) -> None:
        self.successor_id = value

    def __repr__(self) -> str:
        src = self.predecessor.get_label() if self.predecessor is not None else "anon"
        dst = self.successor.get_label() if self.successor is not None else "anon"
        return f"<{self.__class__.__name__}:{src[:6]}->{dst[:6]}>"


class Node(GraphItem):
    """Graph vertex with directional edge navigation and wiring helpers."""

    def edges_in(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Edge]:
        selector = (self.graph._normalize_selector(selector, **criteria) or Selector()).with_criteria(
            successor=self
        )
        return self.graph.find_edges(selector=selector)

    def predecessors(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Node]:
        """Yield immediate predecessor nodes via incoming edges."""
        return (
            edge.predecessor
            for edge in self.edges_in(selector=selector, **criteria)
            if edge.predecessor
        )

    def edges_out(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Edge]:
        selector = (self.graph._normalize_selector(selector, **criteria) or Selector()).with_criteria(
            predecessor=self
        )
        return self.graph.find_edges(selector=selector)

    def successors(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Node]:
        """Yield immediate successor nodes via outgoing edges."""
        return (
            edge.successor
            for edge in self.edges_out(selector=selector, **criteria)
            if edge.successor
        )

    def edges(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Iterator[Edge]:
        """Yield all incident edges (incoming then outgoing)."""
        return itertools.chain(
            self.edges_in(selector=selector, **criteria),
            self.edges_out(selector=selector, **criteria),
        )

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
