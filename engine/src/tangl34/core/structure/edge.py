from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ..entity import Entity
from .node import Node

if TYPE_CHECKING:
    from .graph import Graph

class Edge(Entity):
    src_id: UUID
    dst_id: UUID

    def src(self, g: Graph) -> Node:
        return g.get(self.src_id)

    def dst(self, g: Graph) -> Node:
        return g.get(self.dst_id)
