from functools import total_ordering
from typing import Any, Callable, Iterator, ClassVar, Type

from ..entity import Entity, Registry, Context
from .enums import ServiceKind

@total_ordering
class Handler(Entity):

    func: Callable[[Entity, Context], Any]  # Return type is determined by service
    caller_criteria: dict[str, Any] = None
    priority: int = 0

    def __call__(self, entity, *, ctx: dict, **kwargs):
        return self.func(entity, ctx=ctx, **kwargs)

    def __lt__(self, other):
        return self.priority < other.priority

    def satisfied(self, caller: Entity, ctx) -> bool:
        return not self.predicate(ctx) or caller.match(**self.caller_criteria)
    
class HandlerRegistry(Registry[Handler]):
    
    # decorator
    def register(self, service: ServiceKind, priority: int, caller_criteria: dict[str, Any]): ...
            
    def iter_service(self, service: ServiceKind) -> Iterator[Handler]:
        return iter(sorted(filter(lambda x: x.service is service, self), key=lambda x: x.priority))

    def find_all_for(self, caller: Entity, service: ServiceKind, ctx: Context) -> list[Handler]:
        return list(h for h in self.iter_service(service) if caller.match(**h.caller_criteria) and h.predicate(ctx))

global_handlers = HandlerRegistry()

# Bootstrapping service, handler for gathering handlers

class ScopeController:
    # This is a domain mixin

    @classmethod
    def get_scopes(cls, *entities: HasHandlers) -> Iterator[HandlerRegistry]:
        # ie, ScopeController.get_scopes(domain, node, graph)
        handler_layers = []
        for e in [ entities, global_handlers ]:
            discovery_services = global_handlers.find_all_for(e, Service.SERVICE_DISCOVERY, ctx=None)
            for d in discovery_services:
                handler_layers.extend(d.__call__(e, ctx=None))
        return handler_layers
