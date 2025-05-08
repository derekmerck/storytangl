from collections import defaultdict
from uuid import UUID
from typing import Optional

from ..registry import Registry
from .node import Node
from .edge import Edge

class Graph(Registry[Node]):
    registry: dict[UUID, Node] = {}
    edges_out: dict[UUID, list[Edge]] = defaultdict(list)
    domain: Optional['Domain'] = None
