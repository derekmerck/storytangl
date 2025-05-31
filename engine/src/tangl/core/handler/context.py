from __future__ import annotations

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Node
from .handler_registry import HandlerRegistry

context_handler = HandlerRegistry(default_execute_all_strategy="gather")

class HasContext(Entity):

    locals: StringMap = Field(default_factory=dict)

    @context_handler.register()
    def _provide_my_locals(self, **kwargs):
        return self.locals

    @context_handler.register()
    def _provide_my_self(self,**kwargs):
        return {'self': self}

    def gather_context(self, **kwargs):
        return context_handler.execute_all(self, **kwargs)