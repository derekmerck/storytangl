from __future__ import annotations
from functools import total_ordering
from typing import Any, Callable, ClassVar, Type, TypeVar, Generic, Optional
import logging

from pydantic import model_validator, Field, field_validator

from tangl34.type_hints import StringMap
from ..entity import Entity, Registry
from .enums import ServiceKind

logger = logging.getLogger(__name__)

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
