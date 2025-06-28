from __future__ import annotations
from typing import Iterator, Literal, TYPE_CHECKING
import logging

from pydantic import Field, model_validator

from .graph import GraphItem, Graph

if TYPE_CHECKING:
    from .edge import Edge

class Node(GraphItem):

    def edges(self, *, direction: Literal["in", "out"] = None, **criteria) -> Iterator[Edge]:
        return self.graph.find_edges(self, direction=direction, **criteria)

    def add_edge(self, dest: Node, **kwargs) -> Edge:
        return self.graph.add_edge(self, dest, **kwargs)

    @model_validator(mode='after')
    def _register_with_graph(self):
        if self.graph is not None:
            self.graph.add(self)
        return self
