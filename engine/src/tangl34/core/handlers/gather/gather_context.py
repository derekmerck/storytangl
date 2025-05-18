import functools
from typing import Any, Callable
from collections import ChainMap

from pydantic import Field

from ...type_hints import Context
from ...entity import Entity
from ...structure import Node
from ..handler import Handler
from ..enums import ServiceKind
from ..handler import global_handlers
from ..scope import Scope
from .gather_handlers import gather_handlers


class ContextHandler(Handler[Context]):

    def get_context(self, caller: Node) -> Context:
        return self.func(caller, None)

class HasContext(Entity):

    locals: dict = Field(default_factory=dict)

    @Entity.register("context", priority="late")
    def _provide_locals(self) -> Context:
        return self.locals


def gather_context(caller, *scopes: Scope) -> Context:

    maps = []
    for h in gather_handlers(ServiceKind.GATHER, caller, *scopes):  # type: ContextHandler
        maps.append( h.get_context(caller) )
    return ChainMap( *maps )  # possibly reversed

