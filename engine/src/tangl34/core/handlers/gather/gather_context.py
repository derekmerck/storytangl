from collections import ChainMap

from pydantic import Field

from ...type_hints import Context
from ...entity import Entity
from ..handler import Handler
from ..enums import ServiceKind
from ..scope import Scope
from .gather_handlers import gather_handlers


class HasContext(Entity):
    # Mixin for a scoped Entity subclass

    locals: dict = Field(default_factory=dict)

    # Do this early, locals should clobber other variables
    @Scope.register_handler(ServiceKind.GATHER, priority=10)
    # todo: cast to ContextHandler for return type checking?
    def _provide_locals(self) -> Context:
        return self.locals


class ContextHandler(Handler[Context]):
    # todo: Unnecessary?

    def get_context(self, caller: HasContext) -> Context:
        return self.func(caller, None)


def gather_context(caller, *scopes: Scope) -> Context:

    maps = []
    for h in gather_handlers(ServiceKind.GATHER, caller, *scopes, ctx=None):  # type: ContextHandler
        maps.append( h.func(caller, None) )
    return ChainMap( *maps )  # possibly reversed

