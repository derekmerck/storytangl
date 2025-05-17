from collections import defaultdict

from pydantic import Field

from ..entity import Entity
from .enums import ServiceKind
from .handler import Handler

class ScopeMixin(Entity):
    # One mutable list per ServiceKind, created on demand
    _handlers: dict[str, list[Handler]] = Field(
        default_factory=lambda: defaultdict(list), init=False, repr=False)

    def register(self, service: ServiceKind, handler: Handler):
        self._handlers[service].append(handler)

    def layer(self, service: ServiceKind) -> list[Handler]:
        return self._handlers[service]

global_scope = ScopeMixin()

