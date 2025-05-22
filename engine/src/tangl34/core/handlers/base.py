from __future__ import annotations
from functools import total_ordering
from typing import Any, Callable, ClassVar, Type, TypeVar, Generic, Optional
import logging

from pydantic import model_validator, Field, field_validator

from ..type_hints import StringMap
from ..entity import Entity, Registry
from .enums import ServiceKind

logger = logging.getLogger(__name__)

T = TypeVar("T")

# todo: Cache sorted handler lists per (service, caller class, scopes) as in v33

@total_ordering
class Handler(Entity, Generic[T]):
    # inherits label, predicate, etc from Entity

    func: Callable[[Entity, StringMap], T]  # Return type is determined by service
    service: ServiceKind
    caller_criteria: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    owner_cls: Optional[Type[HasHandlers]] = None
    is_instance_handler: bool = False     # Instance handlers sort before class handlers
    registration_order: int = -1

    @field_validator('caller_criteria', mode="before")
    def _convert_none_to_empty_dict(cls, data):
        if data is None:
            data = {}
        return data

    @model_validator(mode="after")
    def _label_by_func_name(self):
        self.label = f"{self.service.name}:{self.func.__name__}"
        return self

    def __call__(self, entity: Entity, context: StringMap) -> T:
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

    def is_satisfied(self, *, caller: Entity, ctx: StringMap) -> bool:
        return caller.match(**self.caller_criteria) and super().is_satisfied(ctx=ctx)


class HandlerRegistry(Registry[Handler]):

    _global_handler_registration_counter: ClassVar[int] = 0

    def register_handler(self, service: ServiceKind, priority: int=0, caller_criteria=None, owner_cls: Type[HasHandlers] = None, is_instance_handler: bool = False):
        def decorator(func: Callable[[Entity, StringMap], Any]):
            handler = Handler(
                func=func,
                service=service,
                priority=priority,
                caller_criteria=caller_criteria,
                owner_cls=owner_cls,
                is_instance_handler=is_instance_handler,
                # label=getattr(func, "__name__", "anonymous_handler"),
            )
            self.add(handler)
            return func

        return decorator

    def add(self, item: Handler) -> None:
        HandlerRegistry._global_handler_registration_counter += 1
        return super().add(item)

    def find_all(self, **criteria: Any) -> list[Handler]:
        return sorted(super().find_all(**criteria))

    def find_all_for(self, caller: Entity, service: ServiceKind, ctx: StringMap) -> list[Handler]:
        return sorted(
            filter(lambda x: x.service is service and x.is_satisfied(caller=caller, ctx=ctx), self),
            key=lambda x: x.caller_sort_key(caller=caller))

def handler(service_kind, *, priority=10, caller_criteria=None):
    """
    Decorator to tag a method as a handler for a given service.
    """
    def decorator(func):
        func._handler_info = {
            "service_kind": service_kind,
            "priority": priority,
            "caller_criteria": caller_criteria,
        }
        return func
    return decorator

class HasHandlers:
    """
    Generic handler provider: on subclassing, registers all tagged handlers for all services.
    """
    _handler_registry: ClassVar[HandlerRegistry] = HandlerRegistry()

    @classmethod
    def clear_handlers(cls):
        return cls._handler_registry.clear()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Give every subclass its own handler registry
        cls._handler_registry = HandlerRegistry()
        seen = set()
        # Walk this class and all bases (MRO) for any handler-tagged methods
        for base in cls.mro():
            for name, method in base.__dict__.items():
                if getattr(method, "_handler_info", None) and name not in seen:
                    info = method._handler_info
                    cls._handler_registry.register_handler(
                        service=info["service_kind"],
                        priority=info["priority"],
                        caller_criteria=info["caller_criteria"],
                        owner_cls=cls,
                    )(method)
                    seen.add(name)

    @classmethod
    def gather_handlers(cls, service, caller, *objects, ctx=None):
        """
        Aggregate all handlers for the given service, for the given objects (scopes), in priority order.
        """
        from . import global_scope
        if caller not in objects:
            objects = caller, *objects
        if global_scope not in objects:
            objects = *objects, global_scope
        handlers = []
        for obj in objects:
            # for base in type(obj).mro():  # We walk the mro during class creation
            reg = getattr(obj, "_handler_registry", None)
            if reg:
                handlers.extend(reg.find_all_for(caller, service, ctx))
        # Sorting by the handler's sort key
        return sorted(handlers, key=lambda h: h.caller_sort_key(caller))
