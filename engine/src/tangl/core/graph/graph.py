from __future__ import annotations
from uuid import UUID
from typing import Optional, Iterator, Iterable, TYPE_CHECKING
import functools

from pydantic import Field, model_validator

from tangl.type_hints import Identifier
from tangl.utils.hasher import hashing_func
from tangl.core.entity import Entity
from tangl.core.registry import Registry

if TYPE_CHECKING:
    from .subgraph import Subgraph
    from .node import Node
    from .edge import Edge

class GraphItem(Entity):
    """Base abstraction for all graph elements, self-aware"""
    graph: Graph = Field(default=None, exclude=True)
    # graph is for local dereferencing only, do not serialize to prevent recursions
    # hold id only for peer graph items to prevent recursions, see edge

    @model_validator(mode='after')
    def _register_with_graph(self):
        if self.graph is not None:
            self.graph.add(self)
        return self

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


class Graph(Registry[GraphItem]):

    # Stub out mutators
    # def add(self, *args) -> None:
    #     raise NotImplementedError("Graph is read-only")

    # special adds
    def add(self, item: GraphItem) -> None:
        item.graph = self
        super().add(item)

    def add_node(self, *, node_type=None, **attrs) -> Node:
        from .node import Node
        n = Node(node_type=node_type, **attrs)
        self.add(n)
        return n

    def add_edge(self, source: GraphItem, destination: GraphItem, *, edge_type=None, **attrs) -> Edge:
        from .edge import Edge
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
        from .subgraph import Subgraph
        sg = Subgraph(subgraph_type=subgraph_type, **attrs)
        self.add(sg)
        for item in members or ():
            sg.add_member(item)  # validates internally
        return sg

    # special finds
    def find_nodes(self, **criteria) -> Iterator[Node]:
        from .node import Node
        criteria.setdefault("is_instance", Node)
        return self.find_all(**criteria)

    def find_edges(self, **criteria) -> Iterator[Edge]:
        from .edge import Edge
        # find edges in = find_edges(destination=node)
        # find edges out = find_edges(source=node)
        criteria.setdefault("is_instance", Edge)
        return self.find_all(**criteria)

    def find_subgraphs(self, **criteria) -> Iterator[Subgraph]:
        from .subgraph import Subgraph
        criteria.setdefault("is_instance", Subgraph)
        return self.find_all(**criteria)

    def get(self, key: Identifier):
        if isinstance(key, UUID):
            return super().get(key)
        elif isinstance(key, str):
            return self.find_one(label=key) or self.find_one(path=key)

    def _validate_linkable(self, item: GraphItem):
        if not isinstance(item, GraphItem):
            raise TypeError(f"Expected GraphItem, got {type(item)}")
        if item.graph != self:
            raise ValueError(f"Link item must belong to the same graph")
        if item.uid not in self.data:
            raise ValueError(f"Link item must be added to graph first")
        return True

