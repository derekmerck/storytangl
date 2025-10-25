# tangl/core/domain/structural.py

# structural scopes are inferred from an anchor node according to ancestors on a graph.
# for example, ancestors can have their own templates/vars and less frequently, handlers.
# structural domains are mutable b/c they live on the graph, unlike affiliate
# domains, which are frozen because they may be shared across all stories
from typing import Iterator

from tangl.core.graph import Subgraph, Node, Graph  # Graph for pydantic
from .domain import Domain


class DomainGraph(Graph, Domain):
    """A graph that provides a structural domain for registered items"""
    ...


class DomainSubgraph(Subgraph, Domain):
    """A subgraph that provides a structural domain for member items"""
    ...


class DomainNode(Node, Subgraph, Domain):
    """A node that anchors a structural domain for its children"""
    # Should probably be careful that children can only belong to one DomainNode at a time

    def children(self) -> Iterator[Node]:
        return self.members

    def add_child(self, child: Node) -> None:
        """Attach ``child`` to this domain, enforcing single-parent membership."""

        if child.graph is not self.graph:
            raise ValueError("Child node must belong to the same graph as the domain")

        # Remove the child from any existing domain membership to enforce exclusivity.
        try:
            current_parent = child.parent
        except AttributeError:
            current_parent = None

        if current_parent is self:
            # Already attached; make sure both membership and edge exist and return.
            if not self.has_member(child):
                self.add_member(child)
            if self.graph.find_edge(source=self, destination=child, edge_type="child") is None:
                self.add_edge_to(child, edge_type="child")
            return

        if current_parent is not None:
            if isinstance(current_parent, DomainNode):
                current_parent.remove_child(child)
            else:
                current_parent.remove_member(child)

        if not self.has_member(child):
            self.add_member(child)

        if self.graph.find_edge(source=self, destination=child, edge_type="child") is None:
            self.add_edge_to(child, edge_type="child")

    def remove_child(self, child: Node) -> None:
        if not self.has_member(child):
            return

        self.remove_edge_to(child)
        self.remove_member(child)

    def find_children(self, **criteria) -> Iterator[Node]:
        return self.find_all(**criteria)

    def find_child(self, **criteria) -> Node:
        return self.find_one(**criteria)
