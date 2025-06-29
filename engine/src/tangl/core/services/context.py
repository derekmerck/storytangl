from __future__ import annotations
import logging
from typing import Optional, Protocol, Any

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.dispatch import HandlerRegistry, HandlerPriority, HasHandlers

logger = logging.getLogger(__name__)

on_gather_context = HandlerRegistry(label="gather_context", aggregation_strategy="merge")
"""
The global pipeline for gathering context. Handlers for context
should decorate methods with ``@on_gather_context.register(...)``.
"""
class ContextManager:

    def gather_context(self, node: HasContext):
        return node.gather_context()


class HasContext(HasHandlers):

    locals: StringMap = Field(default_factory=dict)

    # Merge in _late_ so they overwrite everything else
    @on_gather_context.register(priority=HandlerPriority.LATE)
    def _provide_my_locals(self, **kwargs) -> StringMap:
        return self.locals

    @on_gather_context.register()
    def _provide_my_self(self, **kwargs) -> StringMap:
        return {'self': self}

    @on_gather_context.register()
    def _provide_is_dirty(self, **kwargs) -> Optional[StringMap]:
        # This should have its own `any_true` pipeline, but we can do it
        # more simply but just only returning a value on True, otherwise
        # None will be ignored when the context is flattened.  If we return
        # False, a late False could clobber an earlier True.
        if not hasattr(self, "is_dirty"):
            raise RuntimeError(f"Non-entity caller: {self!r}")

        if self.is_dirty:
            return {'dirty': True}

    def gather_context(self):
        return on_gather_context.execute_all_for(self, ctx=None)

