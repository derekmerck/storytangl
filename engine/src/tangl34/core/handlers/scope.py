from __future__ import annotations
from typing import ClassVar, Self, Iterator
import functools

from pydantic import PrivateAttr

from ..type_hints import Context
from ..entity import Entity, Singleton
from .enums import ServiceKind
from .handler import Handler, HandlerRegistry

class Scope(Entity):
    # Any class may be a scope for its instances
    _scope_handlers: ClassVar[HandlerRegistry] = HandlerRegistry()
    _scope_priority: ClassVar[int] = 0

    @classmethod
    def clear_handlers(cls):
        cls._scope_handlers.clear()

    def __init_subclass__(cls, **kwargs):
        cls._scope_handlers = HandlerRegistry()
        # Scan for tagged methods and register them
        for name, method in cls.__dict__.items():
            if getattr(method, "_is_scope_handler", False):
                cls._scope_handlers.register(
                    service=method._handler_service,
                    priority=method._handler_priority,
                    caller_criteria=method._handler_caller_criteria,
                    owner_cls=cls,
                )(method)
        super().__init_subclass__(**kwargs)

    # decorator
    @classmethod
    def register_handler(cls, service: ServiceKind, priority=0, caller_criteria=None):
        def decorator(func):
            # Tag the function with handler metadata, to be registered later
            func._is_scope_handler = True
            func._handler_service = service
            func._handler_priority = priority
            func._handler_caller_criteria = caller_criteria
            return func
        return decorator

    @classmethod
    def gather_all_handlers_for(cls, service: ServiceKind, caller: Entity, *scopes: Self, ctx=None) -> Iterator(Handler):
        handlers = []
        seen_registries = set()
        # 1. Add instance handlers first (if available)
        for s in scopes:
            inst_reg = getattr(s, '_instance_handlers', None)
            if inst_reg and id(inst_reg) not in seen_registries:
                handlers.extend(inst_reg.find_all_handlers_for(caller, service, ctx))
                seen_registries.add(id(inst_reg))
        # 2. Now walk the MRO for class-based handler registries
        for s in scopes:
            for base in type(s).mro():
                reg = getattr(base, '_scope_handlers', None)
                if reg and id(reg) not in seen_registries:
                    handlers.extend(reg.find_all_handlers_for(caller, service, ctx))
                    seen_registries.add(id(reg))
        # 3. Optionally add global handlers if not already included
        if global_scope not in scopes:
            handlers.extend(global_scope._scope_handlers.find_all_handlers_for(caller, service, ctx))
        return sorted(handlers, key=lambda h: h.caller_sort_key(caller))


class ScopedSingleton(Singleton, Scope):
    # domains, for example, can also register instance handlers for domain mods, etc
    # restricted to singletons b/c we shouldn't include handler registries on mutable classes
    _instance_handlers: HandlerRegistry = PrivateAttr(default_factory=HandlerRegistry)

    def clear_instance_handlers(self):
        return self._instance_handlers.clear()

    def register_instance_handler(self, service: ServiceKind, func: callable, priority=0, caller_criteria=None):
        # Use the instance's class as owner_cls for correct ordering
        return self._instance_handlers.register(
            service=service,
            priority=priority,
            caller_criteria=caller_criteria,
            owner_cls=type(self),
            is_instance_handler=True
        )(func)


global_scope = Scope(label="global_scope")
# todo: would you ever register instance handlers on global scope, like 'turn on debugging' perhaps
