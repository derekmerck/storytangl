from __future__ import annotations
import logging

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from .handler_registry import HandlerRegistry

logger = logging.getLogger(__name__)

on_gather_context = HandlerRegistry(label="gather_context", default_aggregation_strategy="merge")
"""
The global pipeline for gathering context. Handlers for context
should decorate methods with ``@on_gather_context.register(...)``.
"""

class HasContext(Entity):

    locals: StringMap = Field(default_factory=dict)

    @on_gather_context.register(priority=100)
    def _provide_my_locals(self, *args):
        return self.locals

    @on_gather_context.register()
    def _provide_my_self(self, *args):
        return {'self': self}

    def gather_context(self):
        return on_gather_context.execute_all(self, ctx=None)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        logger.debug(f"Post-init registering _context_ handlers for {cls.__name__}")
        on_gather_context.register_marked_handlers(cls)
