from __future__ import annotations
from typing import Iterator, Union, TypeVar, Generic, Literal, TYPE_CHECKING, Protocol
from uuid import UUID
import itertools
import logging

from pydantic import Field, model_validator

from tangl.core.entity.entity import Entity
from tangl.core.entity.registry import Registry

if TYPE_CHECKING:
    from .node import Node
    from .edge import Edge

logger = logging.getLogger(__name__)

class GraphItem(Entity):

    graph: Graph = Field(None, json_schema_extra={'cmp': False}, exclude=True)


class GraphManager:

    def get(self, graph: Graph, entity_id: UUID) -> GraphItem:
        return graph.get(entity_id)

    def find_edges(self, graph: Graph, node: Node, **criteria) -> Iterator[Edge]:
        return graph.find_edges(node, **criteria)


class Graph(Registry[GraphItem]):

    def add(self, item: GraphItem):
        logger.debug(f"Adding {item!r} to graph {self!r}")
        if item not in self:
            item.graph = self
            super().add(item)
        else:
            raise ValueError(f"Item {item!r} already exists in graph {self!r}")

    def add_edge(self, src: Node, dest: Node, **kwargs) -> Edge:
        from .edge import Edge
        return Edge(src_id=src.uid, dest_id=dest.uid, graph=self, **kwargs)

    def find_edges(self, node: Node, *, direction: Literal["in", "out"] = None, **criteria) -> Iterator[Edge]:
        match direction:
            case "in":
                return self.find_all(dest_id=node.uid, **criteria)
            case "out":
                return self.find_all(src_id=node.uid, **criteria)
            case _:
                return itertools.chain(self.find_all(src_id=node.uid, **criteria), self.find_all(dest_id=node.uid, **criteria))
