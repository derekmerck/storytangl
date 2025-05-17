from typing import Any, Callable

from pydantic import Field

from ...entity import Entity, Context
from ..handler import global_handlers

class HasContext(Entity):

    locals: dict = Field(default_factory=dict)

    @global_handlers.register("context", priority="late")
    def _provide_locals(self) -> Context:
        return self.locals
