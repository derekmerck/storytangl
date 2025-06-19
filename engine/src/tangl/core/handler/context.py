from __future__ import annotations
import logging

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Node, Graph
from tangl.core.dispatch import HandlerRegistry, HandlerPriority, HasHandlers

logger = logging.getLogger(__name__)

on_gather_context = HandlerRegistry(label="gather_context", aggregation_strategy="merge")
"""
The global pipeline for gathering context. Handlers for context
should decorate methods with ``@on_gather_context.register(...)``.
"""

class HasContext(HasHandlers):

    locals: StringMap = Field(default_factory=dict)

    # Merge in _late_ so they overwrite everything else
    @on_gather_context.register(priority=HandlerPriority.LATE)
    def _provide_my_locals(self, **kwargs) -> StringMap:
        return self.locals

    @on_gather_context.register()
    def _provide_my_self(self, **kwargs) -> StringMap:
        return {'self': self}

    def gather_context(self):
        return on_gather_context.execute_all_for(self, ctx=None)
