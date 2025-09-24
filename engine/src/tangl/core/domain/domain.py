# tangl/core/domain/domain.py
from typing import Any

from pydantic import Field

from tangl.info import __version__
from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.dispatch import HandlerRegistry, DEFAULT_HANDLERS

# imported from tangl.__info__
DEFAULT_VARS = {'version': __version__}

class Domain(Entity):
    """
    Domains publish shared identifiers and handlers.  A Scope is an ordered aggregation of Domains
    relative to a particular Node.

    Affiliate domains may be explicitly adopted with a label- or type-based opt-in.

    Structural domains are implicitly assigned by membership in a group, such as a subgraph
    or object class.
    """
    vars: StringMap = Field(default_factory=dict)
    handlers: HandlerRegistry = Field(default_factory=HandlerRegistry)

    def add_vars(self, vars: dict[str, Any]) -> None:
        self.vars.update(vars)

    def add_handler(self, func, **attrs) -> None:
        self.handlers.add(func, **attrs)

    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)


global_domain = Domain(label="globals",
                       vars=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       )
