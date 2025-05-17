from functools import total_ordering
from typing import Any, Callable, Iterator, ClassVar, Type

from pydantic import Field

from ..entity import Entity, Registry, Context
from .enums import Service

# may want to add more services later, like MediaCreation or ServiceResponseProcessing    

@total_ordering
class ServiceHandler(Entity):

    service: Service
    func: Callable[[Entity, Context], Any]  # Return type is determined by service
    caller_criteria: dict[str, Any] = None
    # todo: do we need a "within scope" predicate too?  For linking local only
    priority: int = 0

    def __call__(self, entity, *, ctx: dict, **kwargs):
        return self.func(entity, ctx=ctx, **kwargs)

    def __lt__(self, other):
        return self.priority < other.priority

    def satisfied(self, caller: Entity, ctx) -> bool:
        return not self.predicate(ctx) or caller.match(**self.caller_criteria)
    
class HandlerRegistry(Registry[ServiceHandler]):
    
    # decorator
    def register(self, service: Service, priority: int, caller_criteria: dict[str, Any]): ...
            
    def iter_service(self, service: Service) -> Iterator[ServiceHandler]:
        return iter(sorted(filter(lambda x: x.service is service, self), key=lambda x: x.priority))

    def find_all_for(self, caller: Entity, service: Service, ctx: Context) -> list[ServiceHandler]:
        return list(h for h in self.iter_service(service) if caller.match(**h.caller_criteria) and h.predicate(ctx))

global_handlers = HandlerRegistry()

# Bootstrapping service, handler for gathering handlers

class HasHandlers(Entity):
    
    cls_handler_registry: ClassVar[HandlerRegistry] = HandlerRegistry()
    handler_registry: HandlerRegistry = Field(default_factory=HandlerRegistry)

    @global_handlers.register(Service.SERVICE_DISCOVERY, priority="lower")
    def _provide_cls_handlers(self, service: Service, ctx: dict) -> Iterator[ServiceHandler]:
        return self.cls_handler_registry.find_all_for(self, service, ctx)

    @global_handlers.register(Service.SERVICE_DISCOVERY, priority="higher")
    def _provide_local_handlers(self, service: Service, ctx: dict) -> Iterator[ServiceHandler]:
        return self.handler_registry.find_all_for(self, service, ctx)

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

class ScopedService:
    
    def get_handlers(self, service: Service, *scopes: HasHandlers):
        # todo: do we want to sort by scope, priority or just raw priority and let scopes declare early/late?
        return [ s.iter_service(service) for s in scopes ]