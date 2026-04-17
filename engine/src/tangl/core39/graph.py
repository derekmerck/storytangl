from __future__ import annotations
from uuid import UUID
from typing import Iterator, Optional

from pydantic import PrivateAttr, Field

from .selection import Selector
from .collection import Registry, RegistryAware, EntityGroup

##############################
# GRAPH
##############################

PATH_SYMBOL = "."

class GraphItem(RegistryAware):
    registry: Graph = PrivateAttr(None)

    @property
    def graph(self) -> Graph:
        return self.registry

    def _validate_linkable(self, item: GraphItem):
        if item.graph is not self.graph:
            raise RuntimeError(f"Unlinkable item {item!r}")

class Graph(Registry[GraphItem]):

    def add_node(self, **kwargs) -> Node:
        n = Node(**kwargs)
        self.add(n)
        return n

    def find_nodes(self, s: Selector = None, **criteria) -> Iterator[Node]:
        criteria = criteria or {}
        criteria['has_kind'] = Node
        return self.find_all(s=s, **criteria)

    def add_edge_to(self, node: Node, **kwargs) -> Edge: ...
    def add_edge_from(self, node: Node, **kwargs) -> Edge: ...
    def find_edges_to(self, node: Node, s: Selector = None, **criteria) -> Iterator[Edge]: ...
    def find_edges_from(self, node: Node, s: Selector = None, **criteria) -> Iterator[Edge]: ...

    def add_subgraph(self, *members: Node, **kwargs) -> Subgraph:
        sg = Subgraph(**kwargs)
        for member in members:
            sg.add_member(member)
        self.add(sg)
        return sg

    def find_subgraphs(self, s: Selector = None, **criteria) -> Iterator[Subgraph]:
        criteria = criteria or {}
        criteria['has_kind'] = Subgraph
        return self.find_all(s=s, **criteria)


class Node(GraphItem):
    ...


class Subgraph(GraphItem, EntityGroup[Node]):

    def members(self) -> list[Node]:
        return [self.graph.get(uid) for uid in self.member_ids]  # type: list[Node]

    def add_member(self, value: GraphItem):
        self._validate_linkable(value)
        super().add_member(value)


class Edge(GraphItem):
    predecessor_id: UUID = None
    successor_id: UUID = None

    @property
    def predecessor(self):
        if self.predecessor_id is not None:
            return self.graph.get(self.predecessor_id)
        return None

    @predecessor.setter
    def predecessor(self, value: Node):
        self._validate_linkable(value)
        self.predecessor_id = value.uid

    @property
    def successor(self):
        if self.successor_id is not None:
            return self.graph.get(self.successor_id)
        return None

    @successor.setter
    def successor(self, value: Node):
        self._validate_linkable(value)
        self.successor_id = value.uid

##############################
# DAG
##############################

class HierarchicalNode(Node, Subgraph):

    def parent(self, s: Selector = None, **criteria) -> Optional[HierarchicalNode]:
        # parents can exist on various channels, manifold-parent, concept-parent, etc
        # however, let's assume nodes only belong to a single h-node at a time for now.
        criteria.setdefault('has_kind', HierarchicalNode)
        groups = self.find_groups(s=s, **criteria)  # type: Iterator[HierarchicalNode]
        return next(groups, None)

    def ancestors(self, s: Selector = None, **criteria) -> list[GraphItem]:
        root = self.parent(s=s, **criteria)
        result = []
        while root is not None:
            result.append(root)
            root = root.parent(s, **criteria)
        return result

    def path(self, s: Selector = None, **criteria) -> str:
        ancestors = [self] + self.ancestors(s, **criteria)
        path = PATH_SYMBOL.join(reversed([a.get_label() for a in ancestors]))
        return path

    def add_member(self, item: HierarchicalNode):
        # ensure not in another group or unenroll it
        if not isinstance(item, HierarchicalNode):
            raise TypeError(f"HierarchicalNode expected, got {type(item)}")
        if item.parent() is not None:
            item.parent.remove_member(item)
        super().add_member(item)

