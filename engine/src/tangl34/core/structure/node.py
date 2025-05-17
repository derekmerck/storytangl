from __future__ import annotations
from typing import TYPE_CHECKING, Iterator, Optional
from uuid import UUID

from ..entity import Entity

if TYPE_CHECKING:
    from .graph import Graph
    from .edge import Edge

class Node(Entity):

    def edges(self, g: Graph, **criteria) -> Iterator[Edge]:
        return g.find_edges(self, **criteria)
