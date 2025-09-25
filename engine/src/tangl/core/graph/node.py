# tangl/core/graph/node.py
from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING
from enum import Enum

from .graph import GraphItem, Graph  # Import graph for pydantic

if TYPE_CHECKING:
    from .edge import Edge

class Node(GraphItem):
    node_type: Optional[Enum] = None  # No need to enumerate this yet

    def edges_in(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(destination=self, **criteria)

    def edges_out(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(source=self, **criteria)

    def edges(self, **criteria) -> list[Edge]:
        return list(self.edges_in(**criteria)) + list(self.edges_out(**criteria))

    def add_edge_to(self, node: Node, **attrs) -> None:
        from .edge import Edge
        Edge(source_id=self.uid, destination_id=node.uid, graph=self.graph, **attrs)

    def add_edge_from(self, node: Node, **attrs) -> None:
        from .edge import Edge
        Edge(source_id=node.uid, destination_id=self.uid, graph=self.graph, **attrs)

    def remove_edge_to(self, node: Node) -> None:
        edge = self.graph.find_edge(source=self, destination=node)
        if edge is not None:
            self.graph.remove(edge.uid)

    def remove_edge_from(self, node: Node) -> None:
        edge = self.graph.find_edge(source=node, destination=self)
        if edge is not None:
            self.graph.remove(edge.uid)
