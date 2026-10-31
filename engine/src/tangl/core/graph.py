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
from copy import deepcopy
from functools import cached_property
from fnmatch import fnmatch
from typing import Any, Iterable, Iterator, Mapping, Optional, Protocol, Self, runtime_checkable
from uuid import UUID

from pydantic import Field

from .entity import Entity
from .registry import EntityGroup, HierarchicalGroup, Registry, RegistryAware
from .selector import Selector
from .singleton import Singleton


@runtime_checkable
class TokenDefinitionResolver(Protocol):
    """Optional factory capability for graph-scoped token lookup."""

    def resolve_token_definition(
        self,
        wrapped_cls: type[Singleton],
        token_from: str,
        *,
        graph: Graph | None = None,
    ) -> Singleton | None: ...


def _ancestor_list(item: GraphItem | RegistryAware) -> list[GraphItem | RegistryAware]:
    """Return containment ancestry for graph and hierarchy items.

    ``GraphItem`` exposes ``ancestors()`` as a method, while
    ``HierarchicalGroup`` exposes ``ancestors`` as a property. Core graph
    helpers need to work across both shapes.
    """
    raw_ancestors = getattr(item, "ancestors", None)
    if raw_ancestors is None:
        return []
    if callable(raw_ancestors):
        return list(raw_ancestors())
    return list(raw_ancestors)


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

    @cached_property
    def parent(self) -> GraphItem | None:
        """Return first owning hierarchical graph node, if present.

        Plain :class:`Subgraph` membership is intentionally ignored here. Subgraphs
        are bag-like graph views; only :class:`HierarchicalNode` membership defines
        a single parent path for graph items.
        """
        registry = getattr(self, "registry", None)
        if registry is None:
            return None
        selector = Selector(has_kind=HierarchicalNode, has_member=self)
        return registry.find_one(selector)

    def ancestors(self):
        """Yield containment ancestry from membership-derived parent to root."""
        seen: set[UUID | None] = {getattr(self, "uid", None)}
        current: GraphItem | None = self
        while current is not None:
            parent = getattr(current, "parent", None)
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
            for ancestor in _ancestor_list(self):
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
        for ancestor in _ancestor_list(self):
            pooled.update(getattr(ancestor, "tags", set()) or set())
        return wanted.issubset(pooled)

    def has_ancestor_tags__not(self, tags: set[str]) -> bool:
        """Legacy compatibility negative scope predicate."""
        if not tags:
            return True
        forbidden = set(tags)
        pooled: set[str] = set()
        pooled.update(getattr(self, "tags", set()) or set())
        for ancestor in _ancestor_list(self):
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

    ``Graph`` may also carry an optional singleton ``factory`` authority. This is
    explicitly structured and unstructured by hand so graphs can recover behavior
    registries after persistence. This mirrors the story-layer ``StoryGraph.world``
    round-trip shim and is an interim pattern until core gains generic recursive
    handling for entity-shaped fields.

    Typed find helpers apply narrowing via ``selector.with_criteria(has_kind=...)``.
    Because ``with_criteria`` avoids widening ``has_kind``, callers may narrow kinds
    but cannot widen helper defaults.

    API
    ---
    - :meth:`bind_factory` attaches or clears the singleton graph authority.
    - :meth:`path_dist` ranks candidates by shared containment ancestry.
    - :meth:`unstructure` and :meth:`structure` preserve singleton factory identity
      across graph round-trips.

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

    factory: Any | None = Field(default=None, exclude=True)

    # These maps are a derived view of ``members``. They deliberately store
    # identifiers rather than edge pointers, so copying or pickling a graph
    # cannot retain references into an earlier graph instance.
    __slots__ = (
        "_edges_by_predecessor",
        "_edges_by_successor",
        "_edge_endpoints",
        "_edge_orders",
        "_next_edge_order",
    )

    def model_post_init(self, context: Any) -> None:
        """Build endpoint lookup maps for directly initialized members."""
        super().model_post_init(context)
        self._rebuild_endpoint_index()

    def __copy__(self):
        """Share endpoint lookup state with the shallow-copied members mapping."""
        clone = super().__copy__()
        for name in Graph.__slots__:
            object.__setattr__(clone, name, object.__getattribute__(self, name))
        return clone

    def __deepcopy__(self, memo=None):
        """Deep-copy members through Pydantic, then rebuild endpoint lookup maps."""
        memo = {} if memo is None else memo
        clone = super().__copy__()
        memo[id(self)] = clone
        object.__setattr__(clone, "__dict__", deepcopy(self.__dict__, memo))
        object.__setattr__(clone, "__pydantic_extra__", deepcopy(self.__pydantic_extra__, memo))
        object.__setattr__(clone, "__pydantic_private__", deepcopy(self.__pydantic_private__, memo))
        clone._rebuild_endpoint_index()
        return clone

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Preserve shared shallow-copy state or rebuild for replacement members."""
        clone = super().model_copy(update=update, deep=deep)
        if update is not None and "members" in update:
            clone._rebuild_endpoint_index()
        return clone

    def __setstate__(self, state) -> None:
        """Restore derived endpoint lookup maps after unpickling members."""
        super().__setstate__(state)
        self._rebuild_endpoint_index()

    def _rebuild_endpoint_index(self) -> None:
        """Rebuild the derived endpoint maps from graph membership order."""
        self._edges_by_predecessor: dict[UUID, dict[UUID, None]] = {}
        self._edges_by_successor: dict[UUID, dict[UUID, None]] = {}
        self._edge_endpoints: dict[UUID, tuple[UUID | None, UUID | None]] = {}
        self._edge_orders: dict[UUID, int] = {}
        self._next_edge_order = itertools.count(len(self.members))
        for order, item in enumerate(self.members.values()):
            if isinstance(item, Edge):
                self._edge_orders[item.uid] = order
                self._edge_endpoints[item.uid] = (item.predecessor_id, item.successor_id)
                self._add_endpoint_candidate(self._edges_by_predecessor, item.predecessor_id, item.uid)
                self._add_endpoint_candidate(self._edges_by_successor, item.successor_id, item.uid)

    @staticmethod
    def _add_endpoint_candidate(
        index: dict[UUID, dict[UUID, None]],
        endpoint_id: UUID | None,
        edge_id: UUID,
    ) -> None:
        if endpoint_id is not None:
            index.setdefault(endpoint_id, {})[edge_id] = None

    @staticmethod
    def _remove_endpoint_candidate(
        index: dict[UUID, dict[UUID, None]],
        endpoint_id: UUID | None,
        edge_id: UUID,
    ) -> None:
        if endpoint_id is None or (candidates := index.get(endpoint_id)) is None:
            return
        candidates.pop(edge_id, None)
        if not candidates:
            index.pop(endpoint_id, None)

    def _sync_edge_endpoint_index(self, edge: Edge) -> None:
        """Synchronize one added or rewired edge with the derived maps."""
        if self.members.get(edge.uid) is not edge:
            return
        predecessor_id, successor_id = edge.predecessor_id, edge.successor_id
        previous = self._edge_endpoints.get(edge.uid)
        if previous is not None:
            self._remove_endpoint_candidate(self._edges_by_predecessor, previous[0], edge.uid)
            self._remove_endpoint_candidate(self._edges_by_successor, previous[1], edge.uid)
        self._edge_endpoints[edge.uid] = (predecessor_id, successor_id)
        if edge.uid not in self._edge_orders:
            self._edge_orders[edge.uid] = next(self._next_edge_order)
        self._add_endpoint_candidate(self._edges_by_predecessor, predecessor_id, edge.uid)
        self._add_endpoint_candidate(self._edges_by_successor, successor_id, edge.uid)

    def _remove_edge_endpoint_index(self, edge_id: UUID) -> None:
        """Remove one graph edge from the derived maps."""
        previous = self._edge_endpoints.pop(edge_id, None)
        if previous is None:
            return
        self._remove_endpoint_candidate(self._edges_by_predecessor, previous[0], edge_id)
        self._remove_endpoint_candidate(self._edges_by_successor, previous[1], edge_id)
        self._edge_orders.pop(edge_id, None)

    def _find_endpoint_edges(
        self,
        endpoint_id: UUID,
        index: dict[UUID, dict[UUID, None]],
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        """Filter selector-compatible endpoint candidates in graph insertion order."""
        candidate_ids = index.get(endpoint_id, {})
        candidates = (
            self.members[edge_id]
            for edge_id in sorted(candidate_ids, key=self._edge_orders.__getitem__)
            if isinstance(self.members.get(edge_id), Edge)
        )
        return self._filter_and_sort(candidates, selector=self._typed_selector(Edge, selector))

    def get_authorities(self) -> list[object]:
        """Return application-level behavior registries for dispatch bootstrapping.

        Extension hook — override in application-layer graph subclasses to
        expose domain-specific registries to the VM dispatch chain.

        A bare ``Graph`` delegates to its bound singleton ``factory`` when present.
        Application graphs may override this to add richer authority chains:

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
        authorities: list[object] = []
        get_factory_authorities = getattr(self.factory, "get_authorities", None)
        if callable(get_factory_authorities):
            for authority in get_factory_authorities() or ():
                if all(authority is not existing for existing in authorities):
                    authorities.append(authority)
        return authorities

    def bind_factory(self, value: Singleton | None) -> None:
        """Bind a singleton graph authority used for persistence-safe behavior lookup."""
        if value is not None and not isinstance(value, Singleton):
            raise TypeError("Graph factory must be a Singleton-compatible authority")
        self.factory = value

    def resolve_token_definition(
        self,
        wrapped_cls: type[Singleton],
        token_from: str,
    ) -> Singleton | None:
        """Resolve a token definition through the bound graph factory, when present."""
        if not isinstance(self.factory, TokenDefinitionResolver):
            return None
        return self.factory.resolve_token_definition(
            wrapped_cls,
            token_from,
            graph=self,
        )

    def unstructure(self, *, include_members: bool = True):
        """Return constructor-form graph data including a singleton factory reference."""
        data = super().unstructure(include_members=include_members)
        if self.factory is None or not isinstance(self.factory, Singleton):
            return data
        data["factory"] = self.factory.unstructure()
        return data

    @classmethod
    def structure(cls, data, _ctx=None):
        """Structure a graph and restore any persisted singleton factory reference."""
        def _coerce_kind_refs(value: Any) -> Any:
            if isinstance(value, dict):
                normalized: dict[str, Any] = {}
                for key, item in value.items():
                    if key == "kind" and isinstance(item, str):
                        normalized[key] = Entity.dereference_cls_name(item) or item
                    else:
                        normalized[key] = _coerce_kind_refs(item)
                return normalized
            if isinstance(value, list):
                return [_coerce_kind_refs(item) for item in value]
            return value

        payload = _coerce_kind_refs(dict(data))
        factory_data = payload.get("factory")
        if factory_data is None:
            return super().structure(payload, _ctx=_ctx)
        if isinstance(factory_data, Singleton):
            factory = factory_data
            payload["factory"] = factory
        elif not isinstance(factory_data, dict):
            raise TypeError("Persisted graph factory references must be singleton constructor data")
        else:
            factory = Singleton.structure(dict(factory_data))
            if factory is None:
                raise LookupError(
                    "Persisted graph factory reference could not be resolved to a registered singleton: "
                    f"{factory_data!r}"
                )
            payload["factory"] = factory
        graph = super().structure(payload, _ctx=_ctx)
        graph.bind_factory(factory)
        return graph

    def path_dist(self, a: GraphItem, b: GraphItem) -> int:
        """Return containment distance between two graph items.

        The distance is measured over containment ancestry rather than edge
        traversal. When two items do not share a common ancestor, they receive a
        graph-wide disconnection penalty so connected candidates always sort ahead
        of disconnected ones.
        """
        self._validate_linkable(a)
        self._validate_linkable(b)

        def _chain(item: GraphItem) -> list[GraphItem]:
            return [item, *_ancestor_list(item)]

        a_chain = _chain(a)
        b_chain = _chain(b)
        b_index = {item.uid: idx for idx, item in enumerate(b_chain)}

        for a_idx, item in enumerate(a_chain):
            if item.uid in b_index:
                return a_idx + b_index[item.uid]

        disconnected_penalty = max(1, len(self.members) * 2)
        return disconnected_penalty + len(a_chain) + len(b_chain)

    def add(self, value: GraphItem, _ctx=None) -> None:
        """Dispatch addition, store the resulting member, and index its endpoints."""
        from .ctx import resolve_ctx

        if isinstance(value, RegistryAware):
            value.bind_registry(self)
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            from .dispatch import do_add_item

            value = do_add_item(registry=self, item=value, ctx=_ctx)
        self.members[value.uid] = value
        if isinstance(value, Edge):
            self._sync_edge_endpoint_index(value)
        else:
            self._remove_edge_endpoint_index(value.uid)

    def remove(self, key: UUID, _ctx=None) -> None:
        """Remove an item and its endpoint candidates when it is an edge."""
        super().remove(key, _ctx=_ctx)
        self._remove_edge_endpoint_index(key)

    def clear(self) -> None:
        """Clear graph membership and the derived endpoint maps."""
        super().clear()
        self._edges_by_predecessor.clear()
        self._edges_by_successor.clear()
        self._edge_endpoints.clear()
        self._edge_orders.clear()

    def add_node(self, *, kind=None, **attrs) -> Node:
        """Create and add a node-like graph item."""
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
        predecessor_id = attrs.pop("predecessor_id", None)
        successor_id = attrs.pop("successor_id", None)

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
        kind = kind or Subgraph
        subgraph = kind(**attrs)
        self.add(subgraph)
        for item in members or ():
            subgraph.add_member(item)
        return subgraph

    def _typed_selector(
        self,
        kind: type[GraphItem],
        selector: Selector | None = None,
    ) -> Selector:
        base_selector = self._ensure_selector(selector) or Selector()
        return base_selector.with_criteria(has_kind=kind)

    def _find_typed_all(
        self,
        kind: type[GraphItem],
        selector: Selector | None = None,
    ) -> Iterator[GraphItem]:
        return self.find_all(selector=self._typed_selector(kind, selector))

    def _find_typed_one(
        self,
        kind: type[GraphItem],
        selector: Selector | None = None,
    ) -> GraphItem | None:
        return self.find_one(selector=self._typed_selector(kind, selector))

    def find_subgraphs(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Subgraph]:
        return self._find_typed_all(Subgraph, selector)

    def find_subgraph(
        self,
        selector: Selector | None = None,
    ) -> Optional[Subgraph]:
        return self._find_typed_one(Subgraph, selector)

    @property
    def subgraphs(self) -> list[Subgraph]:
        return list(self.find_subgraphs())

    def find_edges(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        return self._find_typed_all(Edge, selector)

    def find_edges_from(
        self,
        node: Node,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        """Return outgoing edges from one node without scanning unrelated members."""
        return self._find_endpoint_edges(node.uid, self._edges_by_predecessor, selector)

    def find_edges_to(
        self,
        node: Node,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        """Return incoming edges to one node without scanning unrelated members."""
        return self._find_endpoint_edges(node.uid, self._edges_by_successor, selector)

    @property
    def edges(self) -> list[Edge]:
        return list(self.find_edges())

    def find_edge(
        self,
        selector: Selector | None = None,
    ) -> Optional[Edge]:
        return self._find_typed_one(Edge, selector)

    def find_nodes(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Node]:
        return self._find_typed_all(Node, selector)

    @property
    def nodes(self) -> list[Node]:
        return list(self.find_nodes())

    def find_node(
        self,
        selector: Selector | None = None,
    ) -> Optional[Node]:
        return self._find_typed_one(Node, selector)

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
        item._invalidate_parent_attr()
        super().add_member(item)

    def remove_member(self, item: GraphItem, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            self.graph._do_unlink(self, item, _ctx)
        item._invalidate_parent_attr()
        super().remove_member(item)

    def members(self, selector: Selector | None = None, sort_key=None) -> Iterator[GraphItem]:
        """Yield typed graph-item members."""
        return super().members(selector=selector, sort_key=sort_key)


class Edge(GraphItem):
    """Directed connection between predecessor and successor graph items.

    Notes
    -----
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

    def _sync_endpoint_index(self) -> None:
        """Refresh graph-owned endpoint maps when this edge belongs to a graph."""
        if isinstance(self.registry, Graph):
            self.registry._sync_edge_endpoint_index(self)

    def set_predecessor(self, value: Node | UUID | None, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if isinstance(value, UUID):
            endpoint_id = value
            node = self.graph.get(value)
        else:
            endpoint_id = value.uid if value is not None else None
            node = value
        if value is not None and node is None:
            self.predecessor_id = endpoint_id
        elif node is not None:
            self.graph._validate_linkable(node)
            if _ctx is not None:
                self.graph._do_link(self, node, _ctx)
            self.predecessor_id = endpoint_id
        else:
            if _ctx is not None and self.predecessor is not None:
                self.graph._do_unlink(self, self.predecessor, _ctx)
            self.predecessor_id = endpoint_id
        self._sync_endpoint_index()

    @predecessor.setter
    def predecessor(self, value: Node | UUID | None) -> None:
        self.set_predecessor(value)

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id)

    def set_successor(self, value: Node | UUID | None, _ctx=None) -> None:
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if isinstance(value, UUID):
            endpoint_id = value
            node = self.graph.get(value)
        else:
            endpoint_id = value.uid if value is not None else None
            node = value
        if value is not None and node is None:
            self.successor_id = endpoint_id
        elif node is not None:
            self.graph._validate_linkable(node)
            if _ctx is not None:
                self.graph._do_link(self, node, _ctx)
            self.successor_id = endpoint_id
        else:
            if _ctx is not None and self.successor is not None:
                self.graph._do_unlink(self, self.successor, _ctx)
            self.successor_id = endpoint_id
        self._sync_endpoint_index()

    @successor.setter
    def successor(self, value: Node | UUID | None) -> None:
        self.set_successor(value)

    def __repr__(self) -> str:
        src = self.predecessor.get_label() if self.predecessor is not None else "anon"
        dst = self.successor.get_label() if self.successor is not None else "anon"
        return f"<{self.__class__.__name__}:{src[:6]}->{dst[:6]}>"


class Node(GraphItem):
    """Graph vertex with directional edge navigation and wiring helpers."""

    def edges_in(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        selector = (self.graph._ensure_selector(selector) or Selector()).with_criteria(successor=self)
        return self.graph.find_edges_to(self, selector=selector)

    def predecessors(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Node]:
        """Yield immediate predecessor nodes via incoming edges."""
        return (
            edge.predecessor
            for edge in self.edges_in(selector=selector)
            if edge.predecessor
        )

    def edges_out(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        selector = (self.graph._ensure_selector(selector) or Selector()).with_criteria(predecessor=self)
        return self.graph.find_edges_from(self, selector=selector)

    def successors(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Node]:
        """Yield immediate successor nodes via outgoing edges."""
        return (
            edge.successor
            for edge in self.edges_out(selector=selector)
            if edge.successor
        )

    def edges(
        self,
        selector: Selector | None = None,
    ) -> Iterator[Edge]:
        """Yield all incident edges (incoming then outgoing)."""
        return itertools.chain(
            self.edges_in(selector=selector),
            self.edges_out(selector=selector),
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
