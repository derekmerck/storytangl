from uuid import UUID
from enum import Enum, auto
from dataclasses import dataclass, field

from ..entity import Entity

class EdgeKind(Enum):
    HIERARCHY = auto()   # directed, single parent
    ASSOCIATION = auto() # undirected (or symmetric pair)
    PROVIDES = auto()    # requirement → provider
    CHOICE = auto()      # structural node → structural node
    META = auto()        # low-level (e.g., debug)

@dataclass(kw_only=True)
class Edge(Entity):
    src_uid: UUID
    dst_uid: UUID
    kind: EdgeKind
    directed: bool = True
    data: dict | None = field(default_factory=dict)
