# tangl/core/graph/node.py
from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING
from enum import Enum

from .graph import GraphItem, Graph  # Import graph for pydantic

if TYPE_CHECKING:
    from .edge import Edge
    from tangl.ir.story_ir.story_script_models import ScopeSelector

class Node(GraphItem):
    """
    Node(node_type: str)

    Vertex in the topology with convenience accessors for incident edges.

    Why
    ----
    Provides small, composable primitives—nodes plus directional edges—from which
    higher-level narrative structures can be built.

    Key Features
    ------------
    * **Edge navigation** – :meth:`edges_in`, :meth:`edges_out`, :meth:`edges`.
    * **Wiring helpers** – :meth:`add_edge_to`, :meth:`add_edge_from`, and removers.

    API
    ---
    - :meth:`edges_in` / :meth:`edges_out` – iterators filtered by criteria.
    - :meth:`edges` – convenience union of in/out edges.
    - :meth:`add_edge_to` / :meth:`add_edge_from` – create edges within this node's graph.
    - :meth:`remove_edge_to` / :meth:`remove_edge_from` – detach first matching edge if present.
    """

    def edges_in(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(destination=self, **criteria)

    def edges_out(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(source=self, **criteria)

    def edges(self, **criteria) -> list[Edge]:
        return list(self.edges_in(**criteria)) + list(self.edges_out(**criteria))

    def add_edge_to(self, node: Node, **attrs) -> Edge:
        from .edge import Edge
        return Edge(source_id=self.uid, destination_id=node.uid, graph=self.graph, **attrs)

    def add_edge_from(self, node: Node, **attrs) -> Edge:
        from .edge import Edge
        return Edge(source_id=node.uid, destination_id=self.uid, graph=self.graph, **attrs)

    def remove_edge_to(self, node: Node) -> None:
        edge = self.graph.find_edge(source=self, destination=node)
        if edge is not None:
            self.graph.remove(edge.uid)

    def remove_edge_from(self, node: Node) -> None:
        edge = self.graph.find_edge(source=node, destination=self)
        if edge is not None:
            self.graph.remove(edge.uid)

    def has_scope(self, scope: "ScopeSelector | None") -> bool:
        """Return ``True`` when this node satisfies the given scope selector."""

        if scope is None or scope.is_global():
            return True

        if scope.source_label is not None and self.label != scope.source_label:
            return False

        if (
            scope.parent_label is None
            and scope.ancestor_labels is None
            and scope.ancestor_tags is None
        ):
            return True

        if scope.parent_label is not None:
            if not self.has_parent_label(scope.parent_label):
                return False

        if scope.ancestor_labels is not None:
            if not self.has_ancestor_labels(scope.ancestor_labels):
                return False

        if scope.ancestor_tags is not None:
            if not self.has_ancestor_tags(scope.ancestor_tags):
                return False

        return True

    def has_parent_label(self, parent_label: str) -> bool:
        parent = self.parent
        return parent is not None and parent.label == parent_label

    def has_ancestor_labels(self, labels: set[str]) -> bool:
        if not labels:
            return True

        ancestor_labels = {ancestor.label for ancestor in self.ancestors() if ancestor.label}
        return labels.issubset(ancestor_labels)

    def has_ancestor_tags(self, tags: set[str]) -> bool:
        if not tags:
            return True

        ancestor_tags = {
            tag for ancestor in self.ancestors() if ancestor.tags for tag in ancestor.tags
        }
        return tags.issubset(ancestor_tags)
