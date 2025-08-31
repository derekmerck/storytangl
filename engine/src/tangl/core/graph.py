from __future__ import annotations
from enum import Enum
from uuid import UUID
from typing import Optional, Iterator, Iterable
import functools

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.utils.hasher import hashing_func
from .entity import Entity, Registry


class GraphItem(Entity):
    """Base abstraction for all graph elements, self-aware"""
    graph: Graph = Field(default=None,
                         json_schema_extra={"serialize": False,
                                            "compare": False})
    # hold id only for peer graph items to prevent recursions, see edge

    # use cached-property and invalidate if re-parented
    @functools.cached_property
    def parent(self) -> Optional[Subgraph]:
        return next(self.graph.find_subgraphs(has_member=self), None)

    def _invalidate_parent_attr(self):
        # On reparent
        if hasattr(self, "parent"):
            delattr(self, "parent")

    def ancestors(self) -> Iterator[Subgraph]:
        current = self.parent
        while current:
            yield current
            current = current.parent

    def has_ancestor(self, ancestor: Subgraph) -> bool:
        return ancestor in self.ancestors()

    @property
    def root(self) -> Optional[Subgraph]:
        # return the most distant subgraph membership (top-most ancestor)
        last = None
        for anc in self.ancestors():
            last = anc
        return last

    @property
    def path(self):
        # Include self in path
        reversed_ancestors = reversed([self] + list(self.ancestors()))
        return '.'.join([a.get_label() for a in reversed_ancestors])

    def _id_hash(self) -> bytes:
        # Include the graph id if assigned (should always be)
        if self.graph is not None:
            return hashing_func(self.uid, self.__class__, self.graph.uid)
        else:
            return super()._id_hash()

    __hash__ = Entity.__hash__


class Graph(Registry[GraphItem]):

    # Stub out mutators
    # def add(self, *args) -> None:
    #     raise NotImplementedError("Graph is read-only")

    # special adds
    def add(self, item: GraphItem) -> None:
        item.graph = self
        super().add(item)

    def add_node(self, *, node_type=None, **attrs) -> Node:
        n = Node(node_type=node_type, **attrs)
        self.add(n)
        return n

    def add_edge(self, source: GraphItem, destination: GraphItem, *, edge_type=None, **attrs) -> Edge:
        if source is not None:
            self._validate_linkable(source)
            source_id = source.uid
        else:
            source_id = None

        if destination is not None:
            self._validate_linkable(destination)
            destination_id = destination.uid
        else:
            destination_id = None

        e = Edge(source_id=source_id, destination_id=destination_id, edge_type=edge_type, **attrs)
        self.add(e)
        return e

    def add_subgraph(self, *, subgraph_type=None, members: Iterable[GraphItem] = None, **attrs) -> Subgraph:
        sg = Subgraph(subgraph_type=subgraph_type, **attrs)
        self.add(sg)
        for item in members or ():
            sg.add_member(item)  # validates internally
        return sg

    # special finds
    def find_nodes(self, **criteria) -> Iterator[Node]:
        criteria.setdefault("is_instance", Node)
        return self.find(**criteria)

    def find_edges(self, **criteria) -> Iterator[Edge]:
        # find edges in = find_edges(destination=node)
        # find edges out = find_edges(source=node)
        criteria.setdefault("is_instance", Edge)
        return self.find(**criteria)

    def find_subgraphs(self, **criteria) -> Iterator[Subgraph]:
        criteria.setdefault("is_instance", Subgraph)
        return self.find(**criteria)

    def get(self, key: Identifier):
        if isinstance(key, UUID):
            return super().get(key)
        elif isinstance(key, str):
            return self.find_one(label=key) or self.find_one(path=key)

    __hash__ = Entity.__hash__

    def _validate_linkable(self, item: GraphItem):
        if not isinstance(item, GraphItem):
            raise TypeError(f"Expected GraphItem, got {type(item)}")
        if item.graph != self:
            raise ValueError(f"Link item must belong to the same graph")
        if item.uid not in self.data:
            raise ValueError(f"Link item must be added to graph first")
        return True


class Node(GraphItem):
    node_type: Optional[Enum] = None  # No need to enumerate this yet

    def edges_in(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(destination=self, **criteria)

    def edges_out(self, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(source=self, **criteria)

    def edges(self, **criteria) -> list[Edge]:
        return list(self.edges_in(**criteria)) + list(self.edges_out(**criteria))

    __hash__ = Entity.__hash__


class Edge(GraphItem):
    edge_type: Optional[Enum] = None       # No need to enumerate this yet
    source_id:  Optional[UUID] = None      # usually parent
    destination_id: Optional[UUID] = None  # attach to a structure (choice) or dependency (role, loc, etc.)

    @property
    def source(self) -> Optional[GraphItem]:
        return self.graph.get(self.source_id)

    @source.setter
    def source(self, value: Optional[GraphItem]) -> None:
        if value is None:
            self.source_id = None
            return
        self.graph._validate_linkable(value)
        self.source_id = value.uid

    @property
    def destination(self) -> Optional[GraphItem]:
        return self.graph.get(self.destination_id)

    @destination.setter
    def destination(self, value: Optional[Node]) -> None:
        if value is None:
            self.destination_id = None
            return
        self.graph._validate_linkable(value)
        self.destination_id = value.uid

    def __repr__(self) -> str:
        if self.source is not None:
            if self.graph is not None:
                src_label = self.source.label or self.source.short_uid()
            else:
                src_label = self.source_id.hex
        else:
            src_label = "anon"

        if self.destination_id:
            if self.graph is not None:
                dest_label = self.destination.label or self.destination.short_uid()
            else:
                dest_label = self.destination_id.hex
        else:
            dest_label = "anon"

        return f"<{self.__class__.__name__}:{src_label[:6]}->{dest_label[:6]}>"

    __hash__ = Entity.__hash__


class Subgraph(GraphItem):
    subgraph_type: Optional[Enum] = None  # No need to enumerate this yet
    member_ids: list[UUID] = Field(default_factory=list)

    @property
    def members(self) -> Iterator[GraphItem]:
        for member_id in self.member_ids:
            member = self.graph.get(member_id)
            if member is not None:
                yield member

    def has_member(self, node: Node) -> bool:
        return node.uid in self.member_ids

    def add_member(self, item: GraphItem) -> None:
        self.graph._validate_linkable(item)
        item._invalidate_parent_attr()
        self.member_ids.append(item.uid)

    def remove_member(self, item: GraphItem | UUID):
        if isinstance(item, UUID):
            key = item
            item = self.graph.get(key)
        elif isinstance(item, GraphItem):
            key = item.uid
        else:
            raise TypeError(f"Expected UUID or GraphItem, got {type(item)}")
        item._invalidate_parent_attr()
        self.member_ids.remove(key)

    def find(self, *predicates, **criteria) -> Iterator[GraphItem]:
        for member in self.members:
            if member.matches(*predicates, **criteria):
                yield member

    def find_one(self, *predicates, **criteria) -> Optional[GraphItem]:
        return next(self.find(*predicates, **criteria), None)

    __hash__ = Entity.__hash__
