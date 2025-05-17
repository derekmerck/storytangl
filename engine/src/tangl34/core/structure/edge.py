from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID
from enum import Enum

from ..entity import Entity
from .node import Node

if TYPE_CHECKING:
    from .graph import Graph

class EdgeKind(Enum):
    COMPONENT = "component"  # has-a, child
    ASSOCIATE = "associate"  # linked
    PROVIDES = "provides"    # concept provider, in context as role
    CHOICE = "choice"        # structure provider, in choices

class Edge(Entity):
    src_id: UUID
    dst_id: UUID
    edge_kind: Optional[EdgeKind] = None

    def src(self, g: Graph) -> Node:
        return g.get(self.src_id)

    def dst(self, g: Graph) -> Node:
        return g.get(self.dst_id)
