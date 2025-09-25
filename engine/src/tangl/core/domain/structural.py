# structural scopes are inferred from an anchor node according to ancestors on a graph.
# for example, ancestors can have their own templates/vars and less frequently, handlers.

# structural domains are mutable b/c they live on the graph, unlike affiliate
# domains, which are frozen because they may be shared across all stories
from typing import Iterator

from tangl.core.graph import Subgraph, Node
from .domain import Domain

class DomainSubgraph(Subgraph, Domain):
    """A subgraph that provides a structural domain for member items"""
    ...

class DomainNode(Node, Subgraph, Domain):
    """A node that anchors a structural domain for its children"""
    # Should probably be careful that children can only belong to one DomainNode at a time

    def children(self) -> Iterator[Node]:
        return self.members

    def add_child(self, child: Node) -> None:
        self.add_edge_to(child, edge_type="child")
        self.add_member(child)

    def remove_child(self, child: Node) -> None:
        self.remove_edge_to(child)
        return self.remove_member(child)

    def find_children(self, **criteria) -> Iterator[Node]:
        return self.find_members(**criteria)

    def find_child(self, **criteria) -> Node:
        return self.find_member(**criteria)