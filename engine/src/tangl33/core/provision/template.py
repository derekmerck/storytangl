from dataclasses import dataclass, field
from typing import Callable, Mapping

from ..entity import Entity
from ..graph import Node
from ..requirement import Requirement

# todo: want provides and build to be required, but can't put req's after defaults in Entity

@dataclass
class Template(Entity):
    provides: set[str] = field(default_factory=set)
    requires: set[Requirement] = field(default_factory=set)
    build: Callable[[Mapping], Node] = None      # returns a Node; resolver registers
