from __future__ import annotations
from uuid import UUID
from typing import Iterator, Self, Optional
import itertools

from .registry import Registry, RegistryAware, EntityGroup, HierarchicalGroup
from .selector import Selector


class GraphItem(RegistryAware):
    """
    Base for items managed by a Graph.
    """

    @property
    def graph(self) -> Registry[Self]:
        return self.registry


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

    def subgraphs(self, selector: Selector = Selector()) -> Iterator[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_all(selector)

    def edges(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_all(selector)

    def nodes(self, selector: Selector = Selector()) -> Iterator[Node]:
        selector = selector.with_criteria(has_kind=Node)
        return self.find_all(selector)


class Subgraph(EntityGroup, GraphItem):
    # Not necessarily hierarchical, just a bag of graph items

    def members(self, selector: Selector = None) -> Iterator[GraphItem]:
        # Just for type hint
        return super().members(selector=selector)


class Edge(GraphItem):
    """
    dangling edges and connection mutation is allowed bc edges get used for many types of
    logical constructs, some of which don't require pre-resolved endpoints.  Subclasses
    or user must manage consistency.
    """

    predecessor_id: Optional[UUID] = None
    successor_id: Optional[UUID] = None

    @property
    def predecessor(self) -> Optional[Node]:
        return self.registry.get(self.predecessor_id)

    @predecessor.setter
    def predecessor(self, value: Node) -> None:
        if value is not None:
            self.predecessor_id = value.uid
        else:
            self.predecessor_id = None

    @property
    def successor(self) -> Optional[Node]:
        return self.registry.get(self.successor_id)

    @successor.setter
    def successor(self, value: Node) -> None:
        if value is not None:
            self.successor_id = value.uid
        else:
            self.successor_id = None


class Node(GraphItem):
    # Thing that can be connected by edges

    def edges_in(self, selector: Selector) -> Iterator[Edge]:
        selector = selector.with_criteria(successor=self)
        return self.graph.get_edges(selector)

    def edges_out(self, selector: Selector) -> Iterator[Edge]:
        selector = selector.with_criteria(predecessor=self)
        return self.graph.get_edges(selector)

    def edges(self, selector: Selector) -> Iterator[Edge]:
        return itertools.chain(self.edges_in(selector), self.edges_out(selector))


class HierarchicalNode(HierarchicalGroup, Node):
    # todo: should probably enforce uniqueness within hierarchies in the same registry

    # children are both members and items linked by outgoing edges?  No, that's logically too complicated to reason about.  They are distinct concepts.

    def predecessors(self) -> Iterator[Node]:
        """Immediate predecessors via incoming edges."""
        return (e.predecessor for e in self.edges_in() if e.predecessor)
        # or use parent chain?

    def successors(self) -> Iterator[Node]:
        """Immediate successors via outgoing edges."""
        return (e.successor for e in self.edges_out() if e.successor)

    def ancestors(self) -> Iterator[Node]:
        """Transitive predecessors (BFS traversal)."""
        # Implementation needed
