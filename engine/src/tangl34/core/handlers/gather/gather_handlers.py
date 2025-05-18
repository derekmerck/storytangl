from ...type_hints import Context
from ..enums import ServiceKind
from ..scope import Scope
from ..handler import Handler

def gather_handlers(service: ServiceKind, caller, *scopes: Scope, ctx: Context) -> list[Handler]:
    return Scope.gather_all_handlers_for(service, caller, *scopes, ctx=ctx)
