from __future__ import annotations
from typing import TYPE_CHECKING
from collections import defaultdict
from typing import Callable, Dict, List, Tuple

if TYPE_CHECKING:
    from tangl.core35.phase import Phase
    from tangl.core35.model import StoryIR, Patch

Behavior = Callable[["StoryIR"], Tuple["StoryIR", List["Patch"]]]

class BehaviorRegistry:
    """
    Maps Phase → list[(priority:int, behavior)]
    Only the *highest-priority* behavior for a phase is executed in S-1.
    """
    def __init__(self) -> None:
        self._store: Dict[Phase, List[Tuple[int, Behavior]]] = defaultdict(list)

    def register(self, phase: Phase, priority: int = 0):
        def decorator(fn: Behavior) -> Behavior:
            self._store[phase].append((priority, fn))
            # keep list sorted descending
            self._store[phase].sort(key=lambda p: -p[0])
            return fn
        return decorator

    # --- API used by the engine -------------------------------------------
    def get_best(self, phase: Phase) -> Behavior:
        bucket = self._store.get(phase)
        if not bucket:
            raise KeyError(f"No registered behavior for phase {phase}")
        return bucket[0][1]

def _NOOP_BEHAVIOR(ir):
    return ir, []  # returns unchanged IR, no patches
