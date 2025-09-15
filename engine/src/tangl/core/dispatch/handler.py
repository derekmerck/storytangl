from __future__ import annotations
import functools
from enum import IntEnum
from typing import TypeAlias, Any, Callable

from pydantic import ConfigDict

from tangl.type_hints import StringMap as NS
from tangl.core.entity import Entity, Conditional
from .job_receipt import JobReceipt

HandlerFunc: TypeAlias = Callable[[NS], Any]

# this would be better, but pydantic does not like making a schema for it
# class HandlerFunc(Protocol):
#     def __call__(self, ns: StringMap) -> Any: ...

class HandlerPriority(IntEnum):
    """
    Execution priorities for handlers.

    Each TaskHandler is assigned a priority to control high-level ordering.
    The pipeline sorts handlers by these priorities first, with the
    following semantics:

    - :attr:`FIRST` (0) – Runs before all other handlers.
    - :attr:`EARLY` (25) – Runs after FIRST, but before NORMAL.
    - :attr:`NORMAL` (50) – Default middle priority.
    - :attr:`LATE` (75) – Runs after NORMAL, before LAST.
    - :attr:`LAST` (100) – Runs very last in the sequence.

    Users are also free to use any int as a priority. Values lower than 0 will
    run before FIRST, greater than 100 will run after LAST, and other values will
    sort as expected.
    """
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100

@functools.total_ordering
class Handler(Conditional, Entity):
    # handlers take a namespace and return a receipt with a result
    # ordered by distance from caller in scope and reg order

    model_config = ConfigDict(arbitrary_types_allowed=True)

    func: HandlerFunc
    priority: HandlerPriority | int = HandlerPriority.NORMAL
    reg_number: int = -1  # assumes handler in no more than 1 registry

    def __call__(self, ns: NS) -> JobReceipt:
        if not self.available(ns):
            raise RuntimeError(f"Handler {self} not available")
        return JobReceipt(blame_id=self.uid,
                          result=self.func(ns))

    def __lt__(self, other) -> bool:
        # order by priority, then registration number, then uid as a final deterministic tie-breaker
        return (self.priority, self.reg_number, self.uid) < (other.priority, other.reg_number, other.uid)
