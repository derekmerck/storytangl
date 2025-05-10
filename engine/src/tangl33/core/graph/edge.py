from uuid import UUID
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any

from ..entity import Entity

class EdgeKind(Enum):
    HIERARCHY = auto()   # directed, single parent
    ASSOCIATION = auto() # undirected (or symmetric pair)
    PROVIDES = auto()    # requirement → provider
    CHOICE = auto()      # structural node → structural node
    META = auto()        # low-level (e.g., debug)

class ChoiceTrigger(Enum):
    MANUAL = auto()
    BEFORE = auto()
    AFTER = auto()

@dataclass(kw_only=True)
class Edge(Entity):
    src_uid: UUID
    dst_uid: UUID
    kind: EdgeKind
    trigger: ChoiceTrigger = ChoiceTrigger.MANUAL
    directed: bool = True
    # data: dict | None = field(default_factory=dict)
