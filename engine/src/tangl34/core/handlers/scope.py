from __future__ import annotations
from typing import ClassVar, Any, Self
import functools

from pydantic import Field

from ..type_hints import Context
from ..entity import Entity, Singleton
from .enums import ServiceKind
from .handler import Handler, HandlerRegistry

class Scope(Entity):
    # Any class may be a scope for its instances
    _scope_handlers: ClassVar[HandlerRegistry] = HandlerRegistry()
    _scope_priority: ClassVar[int] = 0

    def __init_subclass__(cls, **kwargs):
        cls._scope_handlers = HandlerRegistry()
        super().__init_subclass__(**kwargs)

    # decorator
    @functools.wraps(HandlerRegistry.register)
    def register_handler(self, *args, **kwargs) -> Handler:
        return self._scope_handlers.register_handler(*args, **kwargs)

    @functools.wraps(HandlerRegistry.find_all_handlers_for)
    def find_all_handlers_for(self, *args, **kwargs) -> list[Handler]:
        return self._scope_handlers.find_all_handlers_for(*args, **kwargs)

    @classmethod
    def gather_all_handlers_for(cls, service: ServiceKind, caller: Entity, *scopes: Scope,  ctx: Context) -> list[Handler]:
        # scope ordered, priority ordered within scope
        handlers = []
        for s in scopes:
            handlers.extend( s.find_all_handlers_for(caller, service, ctx) )
        return handlers

    @classmethod
    def discover_scopes(cls, *scopes: Scope) -> list[Scope]:
        return sorted( [ *scopes, global_scope ], key=lambda s: s._scope_priority )

class ScopedSingleton(Singleton, Scope):
    # domains, for example, can also register instance handlers for domain mods, etc
    # restricted to singletons b/c we shouldn't include handler registries on mutable classes
    _instance_handlers: HandlerRegistry = Field(default_factory=HandlerRegistry)

    # decorator
    @functools.wraps(HandlerRegistry.register)
    def register_instance_handler(self, *args, **kwargs) -> Handler:
        return self._instance_handlers.register_handler(*args, **kwargs)

    @functools.wraps(HandlerRegistry.find_all_handlers_for)
    def find_all_handlers_for(self, *args, **kwargs) -> list[Handler]:
        cls_handlers = self._scope_handlers.find_all_handlers_for(*args, **kwargs)
        inst_handlers = self._instance_handlers.find_all_handlers_for(*args, **kwargs)
        return sorted(cls_handlers + inst_handlers, key=lambda h: h.handler_priority)

global_scope = Scope()
