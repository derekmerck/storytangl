from __future__ import annotations
from typing import TYPE_CHECKING
from collections import defaultdict
from dataclasses import dataclass, field

from ..enums import Service
from ..type_hints import StringMap

if TYPE_CHECKING:
    from ..provision import Template

@dataclass(kw_only=True)
class ScopeMixin:
    # ---------------------------------------------------------------------  locals (Context layer)
    locals: StringMap = field(default_factory=dict, metadata=dict(service=Service.CONTEXT))

    # ---------------------------------------------------------------------  private service dicts
    _handlers: dict[Service, list] = field(
        default_factory=lambda: defaultdict(list), init=False, repr=False
    )
    _templates: dict[str, Template] = field(
        default_factory=dict, init=False, repr=False
    )

    # ---------------------------------------------------------------------  public accessors (Scope protocol)
    def handler_layer(self, service: Service | str) -> list:
        """
        Return **this scope’s** capability list for the given service.
        Creates the list on first access so callers can append safely.
        """
        if not isinstance(service, Service):
            service = Service(service)
        return self._handlers[service]

    def add_handler(self, service: Service | str, handler) -> None:
        if handler not in self.handler_layer(service):
            self.handler_layer(service).append(handler)

    def template_layer(self) -> dict[str, Template]:
        """Return this scope’s template mapping (key → Template)."""
        return self._templates

    def local_layer(self) -> StringMap:
        """Return mutable dict stored with the entity (Context layer)."""
        return self.locals
