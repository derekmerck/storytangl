# tangl/core/graph/edge.py
from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING
from enum import Enum
from uuid import UUID

from tangl.core.entity import Entity
from .graph import GraphItem, Graph

from .node import Node

class Edge(GraphItem):
    edge_type: Optional[Enum|str] = None       # No need to enumerate this yet
    source_id:  Optional[UUID] = None          # usually parent
    destination_id: Optional[UUID] = None      # attach to a structure (choice) or dependency (role, loc, etc.)

    @property
    def source(self) -> Optional[Node]:
        return self.graph.get(self.source_id)

    @source.setter
    def source(self, value: Optional[Node]) -> None:
        if value is None:
            self.source_id = None
            return
        self.graph._validate_linkable(value)
        self.source_id = value.uid

    @property
    def destination(self) -> Optional[Node]:
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
            src_label = self.source.label or self.source.short_uid()
        elif getattr(self, 'source_id', None) is not None:
            src_label = self.source_id.hex
        else:
            src_label = "anon"

        if self.destination is not None:
            dest_label = self.destination.label or self.destination.short_uid()
        elif getattr(self, 'destination_id', None) is not None:
            dest_label = self.destination_id.hex
        else:
            dest_label = "anon"

        return f"<{self.__class__.__name__}:{src_label[:6]}->{dest_label[:6]}>"


class AnonymousEdge(Entity):
    # Minimal Edge that does not require a graph, so it can be garbage collected
    source: Node
    destination: Node

    __repr__ = Edge.__repr__

