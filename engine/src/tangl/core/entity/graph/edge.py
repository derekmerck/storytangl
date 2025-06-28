from __future__ import annotations
from typing import TypeVar, Generic, Literal
from uuid import UUID
import logging

from pydantic import Field, model_validator

from tangl.core.entity.entity import Entity
from .graph import GraphItem, Graph
from .node import Node

logger = logging.getLogger(__name__)


class AnonymousEdge(Entity):
    # Minimal Edge that does not require a graph so it can be garbage collected
    source: Node
    dest: Node


SourceT = TypeVar("SourceT", bound=Node)
DestT = TypeVar("DestT", bound=Node)

class Edge(GraphItem, Generic[SourceT, DestT]):

    src_id: UUID
    dest_id: UUID

    @property
    def src(self) -> SourceT:
        return self.graph.get(self.src_id)

    @src.setter
    def src(self, node: SourceT):
        self.src_id = node.uid

    @property
    def dest(self) -> DestT:
        return self.graph.get(self.dest_id)

    @dest.setter
    def dest(self, node: DestT):
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
