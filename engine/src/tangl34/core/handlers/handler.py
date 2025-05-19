from functools import total_ordering
from typing import Any, Callable, Iterator, ClassVar, Type, TypeVar, Generic

from ..entity import Entity, Registry, Context
from .enums import ServiceKind

T = TypeVar("T")

@total_ordering
class Handler(Entity, Generic[T]):

    func: Callable[[Entity, Context], T]  # Return type is determined by service
    service: ServiceKind
    caller_criteria: dict[str, Any] = None
    priority: int = 0
    owner_cls: Type[Entity] = Entity
    is_instance_handler: bool = False     # Instance handlers sort before class handlers
    registration_order: int = -1

    def __call__(self, entity: Entity, context: Context) -> T:
        return self.func(entity, context)

    def __lt__(self, other):
        return (self.priority, self.registration_order) < (other.priority, other.registration_order)

    def caller_sort_key(self, caller: Entity):

        def class_depth_for(_caller, owner_cls):
            """Return MRO index: 0 for direct match, 1 for parent, etc. Large for unrelated."""
            try:
                return _caller.__class__.mro().index(owner_cls)
            except ValueError:
                return 999  # Arbitrarily large if not in hierarchy

        return (self.priority,
                not self.is_instance_handler,
                class_depth_for(caller, self.owner_cls),
                self.registration_order)

    def satisfied(self, *, caller: Entity, ctx: Context) -> bool:
        return caller.match(**self.caller_criteria) and super().satisfied(ctx=ctx)

class HandlerRegistry(Registry[Handler]):

    _global_handler_registration_counter: ClassVar[int] = 0

    def add(self, item: Handler) -> None:
        HandlerRegistry._global_handler_registration_counter += 1
        return super().add(item)

    def register(self, service: ServiceKind, priority: int = 0, caller_criteria: dict[str, Any] = None, owner_cls: Type[Entity] = Entity, is_instance_handler: bool = False) -> None:
        def decorator(func: Callable[[Entity, Context], Any]):
            handler = Handler(
                func=func,
                service=service,
                priority=priority,
                caller_criteria=caller_criteria or {},
                owner_cls=owner_cls,
                registration_order=self._global_handler_registration_counter,
                is_instance_handler=is_instance_handler,
                label=getattr(func, "__name__", "anonymous_handler"),
            )
            self.add(handler)
            return func

        return decorator

    def iter_handlers(self, service: ServiceKind) -> Iterator[Handler]:
        return iter(sorted(filter(lambda x: x.service is service, self)))

    def find_all_handlers_for(self, caller: Entity, service: ServiceKind, ctx: Context) -> list[Handler]:
        return list(
            iter(
                sorted(
                    filter(
                        lambda x: x.service is service and x.satisfied(caller=caller, ctx=ctx), self),
                    key=lambda x: x.caller_sort_key(caller=caller)
                )
            )
        )
