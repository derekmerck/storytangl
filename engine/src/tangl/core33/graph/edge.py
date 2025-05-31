from uuid import UUID
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any

from ..entity import Entity
from ..type_hints import StringMap

class EdgeKind(Enum):
    HIERARCHY = auto()   # directed, single parent
    ASSOCIATION = auto() # undirected (or symmetric pair)
    PROVIDES = auto()    # requirement → provider
    CHOICE = auto()      # structural node → structural node
    META = auto()        # low-level (e.g., debug)

class EdgeState(Enum):
    LATENT = auto()
    RESOLVED = auto()
    OPEN = auto()
    VISITED = auto()

# todo: this belongs with service.choice, choices should return edges with triggers
#       its part of the choice cap, not of the edge?
class ChoiceTrigger(Enum):
    MANUAL = auto()
    BEFORE = auto()
    AFTER = auto()

@dataclass(kw_only=True)
class Edge(Entity):
    src_uid: UUID
    dst_uid: UUID
    kind: EdgeKind
    state: EdgeState = EdgeState.LATENT  # starts out as a potential edge
    trigger: ChoiceTrigger = ChoiceTrigger.MANUAL
    directed: bool = True
    # data: dict | None = field(default_factory=dict)
    # use _locals_ instead to match entity expectations
    locals: StringMap = field(default_factory=dict)
