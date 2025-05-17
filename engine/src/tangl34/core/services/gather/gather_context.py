from typing import Any, Callable
from collections import ChainMap

from pydantic import Field

from ...entity import Entity, Context
from ..enums import ServiceKind
from ..handler import global_handlers
from .gather_handlers import gather_handlers

class HasContext(Entity):

    locals: dict = Field(default_factory=dict)

    @global_handlers.register("context", priority="late")
    def _provide_locals(self) -> Context:
        return self.locals


def gather_context(*scopes) -> Context:

    maps = []
    for h in gather_handlers(ServiceKind.GATHER, *scopes):
        maps.append( h.get_context() )
    return ChainMap( *maps )  # possibly reversed

