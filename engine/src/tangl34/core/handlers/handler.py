from functools import total_ordering
from typing import Any, Callable, Iterator, ClassVar, Type, TypeVar, Generic

from ..entity import Entity, Registry, Context
from .enums import ServiceKind

T = TypeVar("T")

@total_ordering
class Handler(Entity, Generic[T]):

    func: Callable[[Entity, Context], T]  # Return type is determined by service
    caller_criteria: dict[str, Any] = None
    priority: int = 0

    def __lt__(self, other):
        return self.priority < other.priority

    def satisfied(self, *, caller: Entity, ctx: Context) -> bool:
        return not caller.match(**self.caller_criteria) or not super().satisfied(ctx=ctx)

class HandlerRegistry(Registry[Handler]):
    
    # decorator
    def register(self, service: ServiceKind, priority: int, caller_criteria: dict[str, Any]): ...
            
    def iter_handlers(self, service: ServiceKind) -> Iterator[Handler]:
        return iter(sorted(filter(lambda x: x.service is service, self), key=lambda x: x.priority))

    def find_all_handlers_for(self, caller: Entity, service: ServiceKind, ctx: Context) -> list[Handler]:
        return list(h for h in self.iter_service(service) if caller.match(**h.caller_criteria) and h.predicate(ctx))

global_handlers = HandlerRegistry()
