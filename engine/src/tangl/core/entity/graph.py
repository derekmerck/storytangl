from __future__ import annotations
from typing import Iterator, Union, TypeVar, Generic, Literal
from uuid import UUID
import itertools
import logging

from pydantic import Field, model_validator

from .entity import Entity
from .registry import Registry

logger = logging.getLogger(__name__)

class Node(Entity):

    graph: Graph = Field(None, json_schema_extra={'cmp': False}, exclude=True)

    def edges(self, *, direction: Literal["in", "out"] = None, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(self, direction=direction, **criteria)

    def add_edge(self, dest: Node, **kwargs) -> Edge:
        return self.graph.add_edge(self, dest, **kwargs)

    @model_validator(mode='after')
    def _register_with_graph(self):
        if self.graph is not None:
            self.graph.add(self)
        return self


class AnonymousEdge(Entity):
    # Minimal Edge that does not require a graph so it can be garbage collected
    source: Node
    dest: Node


NodeT = TypeVar("NodeT", bound=Node)

class Edge(Entity, Generic[NodeT]):
    graph: Graph = Field(None, json_schema_extra={'cmp': False}, exclude=True)

    src_id: UUID
    dest_id: UUID

    @property
    def src(self) -> Node:
        return self.graph.get(self.src_id)

    @src.setter
    def src(self, node: Node):
        self.src_id = node.uid

    @property
    def dest(self) -> NodeT:
        return self.graph.get(self.dest_id)

    @dest.setter
    def dest(self, node: NodeT):
        self.dest_id = node.uid

    def __repr__(self) -> str:
        if self.src_id:
            if self.graph is not None:
                src_label = self.src.label
            else:
                src_label = self.src_id.hex
        else:
            src_label = "anon"

        if self.dest_id:
            if self.graph is not None:
                dest_label = self.dest.label
            else:
                dest_label = self.dest_id.hex
        else:
            dest_label = "anon"

        return f"<{self.__class__.__name__}:{src_label[:6]}->{dest_label[:6]}>"

    @model_validator(mode='after')
    def _register_with_graph(self):
        if self.graph is not None:
            self.graph.add(self)
        return self

class Graph(Registry[Union[Node, Edge]]):

    def add(self, item: Node | Edge):
        logger.debug(f"Adding {item!r} to graph {self!r}")
        if item not in self:
            item.graph = self
            super().add(item)
        else:
            raise ValueError(f"Item {item!r} already exists in graph {self!r}")

    def add_edge(self, src: Node, dest: Node, **kwargs) -> Edge:
        return Edge(src_id=src.uid, dest_id=dest.uid, graph=self, **kwargs)

    def find_edges(self, node: Node, *, direction: Literal["in", "out"] = None, **criteria) -> Iterator[Edge]:
        match direction:
            case "in":
                return self.find_all(dest_id=node.uid, **criteria)
            case "out":
                return self.find_all(src_id=node.uid, **criteria)
            case _:
                return itertools.chain(self.find_all(src_id=node.uid, **criteria), self.find_all(dest_id=node.uid, **criteria))
