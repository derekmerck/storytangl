from __future__ import annotations
import functools
from enum import IntEnum, Enum
from typing import TypeAlias, Any, Callable, Optional

from pydantic import ConfigDict

from tangl.type_hints import StringMap as NS
from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity, Selectable, is_identifier
from .job_receipt import JobReceipt

# todo: this is an entity handler, should include the caller and caller's current scope _or_
#       it's handlers/ns
#       may want to include prior results/artifacts in the ns, or as a side-channel?

# HandlerFunc: TypeAlias = Callable[[Entity, NS], Any]
HandlerFunc: TypeAlias = Callable[[NS], Any]

# this would be better, but pydantic does not like making a schema for it
# class HandlerFunc(Protocol):
#     def __call__(self, ns: StringMap) -> Any: ...

class HandlerPriority(IntEnum):
    """
    Execution priorities for handlers.

    Each Handler is assigned a priority to control high-level ordering.
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
class Handler(HasSeq, Selectable, Entity):
    # handlers take a namespace and return a receipt with a result
    # ordered by distance from caller in scope and instance seq

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    func: HandlerFunc
    priority: HandlerPriority | int = HandlerPriority.NORMAL
    result_type: Optional[Enum | str] = None  # No need to enumerate this yet

    def has_func_name(self, value: str) -> bool:
        return self.func.__name__ == value

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.func.__name__

    def __call__(self, ns: NS) -> JobReceipt:
        return JobReceipt(blame_id=self.uid,
                          result=self.func(ns),
                          result_type=self.result_type)

    def __lt__(self, other) -> bool:
        # order by priority, then registration number (may duplicate if merging registries),
        # then uid as a final deterministic tie-breaker
        return (self.priority, self.seq, self.uid) < (other.priority, other.seq, other.uid)
