from __future__ import annotations
from uuid import UUID
from typing import Iterator, Self, Optional
import itertools

from pydantic import Field

from .registry import Registry, RegistryAware, EntityGroup, HierarchicalGroup
from .selector import Selector


class GraphItem(RegistryAware):
    """
    Base for items managed by a Graph.
    """
    registry: Graph = Field(None, exclude=True)  # change type hint

    @property
    def graph(self) -> Graph:
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

    def get_subgraphs(self, selector: Selector = Selector()) -> Iterator[Subgraph]:
        selector = selector.with_criteria(has_kind=Subgraph)
        return self.find_all(selector)

    def get_edges(self, selector: Selector = Selector()) -> Iterator[Edge]:
        selector = selector.with_criteria(has_kind=Edge)
        return self.find_all(selector)

    def get_nodes(self, selector: Selector = Selector()) -> Iterator[Node]:
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
        return self.graph.get(self.predecessor_id)

    @predecessor.setter
    def predecessor(self, value: Node) -> None:
        if value is not None:
            self.predecessor_id = value.uid
        else:
            self.predecessor_id = None

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id)

    @successor.setter
    def successor(self, value: Node) -> None:
        if value is not None:
            self.successor_id = value.uid
        else:
            self.successor_id = None


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


class HierarchicalNode(HierarchicalGroup, Node):
    ...
