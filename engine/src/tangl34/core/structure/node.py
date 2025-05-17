from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID

from ..entity import Entity

if TYPE_CHECKING:
    from .graph import Graph
    from .edge import Edge

class Node(Entity):

    edge_ids: list[UUID]

    def edges(self, g: Graph, **criteria) -> list[Edge]:
        return [g.get(e) for e in self.edge_ids if g.get(e).match(**criteria)]
