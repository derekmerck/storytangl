from typing import Mapping, Callable, Literal

from pydantic.dataclasses import dataclass

@dataclass
class ContextProvider:
    provide: Callable[[dict], Mapping]
    tier: str = "node"
    phase: Literal['early', 'late'] = 'late'
    predicate: Callable[[dict], bool] = lambda ctx: True

