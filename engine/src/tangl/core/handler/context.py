from __future__ import annotations
import logging

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from .handler_registry import HandlerRegistry

logger = logging.getLogger(__name__)

context_handler = HandlerRegistry(label="context_handler", default_aggregation_strategy="merge")

class HasContext(Entity):

    locals: StringMap = Field(default_factory=dict)

    @context_handler.register(priority=100)
    def _provide_my_locals(self, *args):
        return self.locals

    @context_handler.register()
    def _provide_my_self(self, *args):
        return {'self': self}

    def gather_context(self):
        return context_handler.execute_all(self, ctx=None)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        logger.debug(f"Post-init registering _context_ handlers for {cls.__name__}")
        context_handler.register_marked_handlers(cls)
