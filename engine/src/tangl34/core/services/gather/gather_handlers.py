from typing import Iterator, Optional

from ..enums import ServiceKind
from ..scope import ScopeMixin
from ..handler import Handler

def gather_handlers(service: ServiceKind, *scopes: ScopeMixin, **criteria) -> list[Handler]:
    handlers = []
    for s in scopes:
        layer = s.layer(service)
        handlers.extend( [ h for h in layer if h.match(**criteria)] )
    return sorted(handlers, key=lambda h: h.priority)
