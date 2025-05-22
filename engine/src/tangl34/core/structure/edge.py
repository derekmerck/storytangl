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
    REQUIREMENT = "requirement"  # complement direction of a provider
    PROVIDES = "provides"    # concept provider, included in context as role
    CHOICE = "choice"        # structure provider, included in choices
    BLAME = "blame"          # produced by/for, used for feed-backwards analysis

class Edge(Entity):
    src_id: UUID
    dst_id: UUID
    edge_kind: Optional[EdgeKind] = None

    def src(self, g: Graph) -> Node:
        return g.get(self.src_id)

    def dst(self, g: Graph) -> Node:
        return g.get(self.dst_id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{str(self.src_id)[:6]}->{str(self.dst_id)[:6]}>"

