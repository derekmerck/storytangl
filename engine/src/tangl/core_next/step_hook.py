from __future__ import annotations
from typing import Literal, Callable, Optional, TYPE_CHECKING
from pydantic.dataclasses import dataclass

from .entity import Entity
from .edge import Edge

@dataclass
class StepHook:
    phase: Literal['before_redirect', 'after_render', 'final']
    predicate: Callable[[dict], bool]
    action: Callable[[Entity, dict], Optional[Edge]]
    priority: int = 0
    tier: str = "graph"   # global | domain | graph | node
