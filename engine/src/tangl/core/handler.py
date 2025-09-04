from __future__ import annotations
import functools
from enum import IntEnum
from typing import TypeAlias, Literal, Any, ClassVar, Iterator, Optional, Iterable, Callable, Protocol
from uuid import UUID

from pydantic import model_validator, Field, ConfigDict

from tangl.type_hints import Predicate, StringMap
from .entity import Entity, Registry, Conditional

NS = StringMap

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
class JobReceipt(Entity):

    blame_id: UUID | tuple[UUID, ...]  # blame
    result: Any
    seq: int

    @model_validator(mode="before")
    @classmethod
    def _set_seq(cls, data: StringMap):
        data = dict(data or {})
        if data.get('seq') is None:   # unassigned or passed none
            # Don't want to incr if not using it
            data['seq'] = cls.incr_count()
        return data

    _instance_count: ClassVar[int] = 0

    @classmethod
    def incr_count(cls) -> int:
        cls._instance_count += 1
        return cls._instance_count

    def __lt__(self, other: Any) -> bool:
        # Sorts non-receipts to the front without raising
        return self.seq < getattr(other, 'seq', -1)

@functools.total_ordering
class Handler(Conditional, Entity):
    # handlers take a namespace and return a receipt with a result
    # ordered by distance from caller in scope and reg order

    model_config = ConfigDict(arbitrary_types_allowed=True)

    func: HandlerFunc
    priority: HandlerPriority | int = HandlerPriority.NORMAL
    reg_number: int = -1  # assumes handler in no more than 1 registry

    def __call__(self, ns: StringMap) -> JobReceipt:
        if not self.available(ns):
            raise RuntimeError(f"Handler {self} not available")
        return JobReceipt(blame_id=self.uid,
                          result=self.func(ns))

    def __lt__(self, other) -> bool:
        # order by priority, then registration number, then uid as a final deterministic tie-breaker
        return (self.priority, self.reg_number, self.uid) < (other.priority, other.reg_number, other.uid)

class HandlerRegistry(Registry[Handler]):

    def add(self, func: HandlerFunc, **attrs):
        h = Handler(func=func, reg_number=len(self), **attrs)
        super().add(h)

    def register(self, **attrs):
        def decorator(func: HandlerFunc):
            self.add(func, **attrs)
            return func
        return decorator

    def find_all(self, **criteria) -> Iterator[Handler]:
        yield from sorted(super().find_all(**criteria))

    def run_one(self, ns: StringMap, **criteria) -> Optional[JobReceipt]:
        _handlers = self.find_all(**criteria)
        h = next(_handlers, None)
        return h(ns) if h else None

    def run_all(self, ns: StringMap, *predicates, **criteria) -> Iterator[JobReceipt]:
        _handlers = self.find_all(*predicates, **criteria)
        for h in _handlers:
            yield h(ns)

    @classmethod
    def run_handlers(cls, ns: StringMap, handlers: Iterable[Handler]) -> Iterator[JobReceipt]:
        # useful when merging handlers from multiple sources
        # deterministic ascending order: FIRST→LAST, reg_number, uid
        _handlers = sorted(handlers)
        for h in _handlers:
            yield h(ns)

DEFAULT_HANDLERS = HandlerRegistry()
