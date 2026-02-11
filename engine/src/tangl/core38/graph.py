# tangl/core/graph.py
from __future__ import annotations
from uuid import UUID
from typing import Iterator, Optional, Iterable
import itertools
from types import SimpleNamespace

from pydantic import model_validator

from .registry import Registry, RegistryAware, EntityGroup, HierarchicalGroup
from .selector import Selector


class GraphItem(RegistryAware):
    """
    Base for items managed by a Graph.
    """
    @property
    def graph(self) -> Graph:
        return self._registry


class Graph(Registry[GraphItem]):
    """
    Specialized registry for nodes and edges.

    Shape concerns (Core):
    - Registry of GraphItems indexed by uid
    - Convenience accessors for nodes/edges
    - Pure topology queries (successors, predecessors)

    Behavioral concerns (VM):
    - Cursor/traversal semantics
    - Availability evaluation
    - Frontier discovery
    """

    # Typed creation helpers

    def add_node(self, *, kind=None, **attrs) -> Node:
        kind = kind or Node
        n = kind.structure(**attrs)
        self.add(n)
        return n

    def add_edge(self, predecessor: GraphItem, successor: GraphItem, *, kind=None, **attrs) -> Edge:
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
        e = kind.structure(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            **attrs)
        self.add(e)
        return e

    def add_subgraph(self, *, kind=None, members: Iterable[GraphItem] = None, **attrs) -> Subgraph:
        kind = kind or Subgraph
        sg = kind.structure(**attrs)
        self.add(sg)
        for item in members or ():
            sg.add_member(item)  # validates internally
        return sg

    # Typed finder helpers

    def find_subgraphs(self, selector: Selector = Selector()) -> Iterator[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_all(selector)

    def find_subgraph(self, selector: Selector = Selector()) -> Iterator[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_one(selector)

    def find_edges(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_all(selector)

    def find_edge(self, selector: Selector = Selector()) -> Edge:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_one(selector)

    def find_nodes(self, selector: Selector = Selector()) -> Iterator[Node]:
        selector = selector.with_criteria(has_kind=Node)
        return self.find_all(selector)

    def find_node(self, selector: Selector = Selector()) -> Iterator[Node]:
        selector = selector.with_criteria(has_kind=Node)
        return self.find_one(selector)

    # Utilities

    def _validate_linkable(self, item: GraphItem):
        if not isinstance(item, GraphItem):
            raise TypeError(f"Expected GraphItem, got {type(item)}")
        if item.graph != self:
            raise ValueError(f"Link item must belong to the same graph")
        if item.uid not in self.members:
            raise ValueError(f"Link item must be added to graph first")
        return True

    def _do_link(self, caller: GraphItem, node: Node, _ctx):
        # called by subgraphs for adding members, edges for setting predecessor/successor
        from .dispatch import do_link
        return do_link(caller=caller, node=node, ctx=_ctx)

    def _do_unlink(self, caller: GraphItem, node: Node, _ctx):
        # called by subgraphs for removing members, edges for setting predecessor/successor to None
        from .dispatch import do_unlink
        return do_unlink(caller=caller, node=node, ctx=_ctx)


class Subgraph(EntityGroup, GraphItem):
    # Not necessarily hierarchical, just a bag of graph items

    def add_member(self, item: GraphItem, _ctx = None):
        self.graph._validate_linkable(item)
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            self.graph._do_link(self, item, _ctx)
        return super().add_member(item)

    def remove_member(self, item: GraphItem, _ctx = None):
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            self.graph._do_unlink(self, item, _ctx)
        super().remove_member(item)

    def members(self, selector: Selector = None, sort_key = None) -> Iterator[GraphItem]:
        # Just for type hint
        return super().members(selector=selector)


class Edge(GraphItem):
    """
    dangling edges and connection mutation is allowed bc edges get used for many types of
    logical constructs, some of which don't require pre-resolved endpoints.  Subclasses
    or user must manage consistency.

    Example:
        >>> g = Graph()
        >>> n = Node(registry=g)
        >>> e = Edge(label='e', registry=g, successor_id=n.uid)
        >>> g.find_one(Selector(successor=n))
        <Edge:e>
        >>> from .behavior import BehaviorRegistry; br = BehaviorRegistry()
        >>> _ = br.register(func=lambda *args, **kwargs: print('foo'), task="link")
        >>> ctx = SimpleNamespace(get_registries=lambda: [br])
        >>> e.set_predecessor(n, ctx)
        foo
        >>> from .ctx import using_ctx
        >>> with using_ctx(ctx):  # use ambient ctx to trigger hooks when setting prop
        ...     e.predecessor = n
        foo
    """

    predecessor_id: Optional[UUID] = None
    successor_id: Optional[UUID] = None

    @property
    def predecessor(self) -> Optional[Node]:
        return self.graph.get(self.predecessor_id)

    def set_predecessor(self, value: Node, _ctx = None):
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if value is not None:
            self.graph._validate_linkable(value)
            if _ctx is not None:
                self.graph._do_link(self, value, _ctx)
            self.predecessor_id = value.uid
        else:
            if _ctx is not None:
                self.graph._do_unlink(self, self.predecessor, _ctx)
            self.predecessor_id = None

    @predecessor.setter
    def predecessor(self, value: Node) -> None:
        # todo: setting prop directly won't trigger hooks until global
        #       `with context` manager is implemented for dispatch
        self.set_predecessor(value)

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id)

    def set_successor(self, value: Node, _ctx = None):
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if value is not None:
            self.graph._validate_linkable(value)
            if _ctx is not None:
                self.graph._do_link(self, value, _ctx)
            self.successor_id = value.uid
        else:
            if _ctx is not None:
                self.graph._do_unlink(self, self.successor, _ctx)
            self.successor_id = None

    @successor.setter
    def successor(self, value: Node) -> None:
        # todo: setting prop directly won't trigger hooks until global
        #       `with context` manager is implemented for dispatch
        self.set_successor(value)


class Node(GraphItem):
    # Thing that can be connected by edges

    def edges_in(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(successor=self)
        return self.graph.get_edges(selector)

    def predecessors(self, selector: Selector = None) -> Iterator[Node]:
        """Immediate predecessors via incoming edges."""
        return (e.predecessor for e in self.edges_in(selector) if e.predecessor)

    def edges_out(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(predecessor=self)
        return self.graph.get_edges(selector)

    def successors(self, selector = None) -> Iterator[Node]:
        """Immediate successors via outgoing edges."""
        return (e.successor for e in self.edges_out(selector) if e.successor)

    def edges(self, selector: Selector = None) -> Iterator[Edge]:
        return itertools.chain(self.edges_in(selector), self.edges_out(selector))

    # Connector helpers

    def add_edge_to(self, node: Node, kind=None, **attrs) -> Edge:
        return self.graph.add_edge(self, node, kind=kind, **attrs)

    def add_edge_from(self, node: Node, kind=None, **attrs) -> Edge:
        return self.graph.add_edge(self, node, kind=kind, **attrs)

    def remove_edge_to(self, node: Node) -> None:
        edge = self.graph.find_edge(source=self, destination=node)
        if edge is not None:
            self.graph.remove(edge.uid)

    def remove_edge_from(self, node: Node) -> None:
        edge = self.graph.find_edge(source=node, destination=self)
        if edge is not None:
            self.graph.remove(edge.uid)



class HierarchicalNode(HierarchicalGroup, Node):
    ...
