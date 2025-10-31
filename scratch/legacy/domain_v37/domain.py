# tangl/core/domain/domain.py
from typing import Any

from pydantic import Field

from tangl.info import __version__
from tangl.type_hints import StringMap
from tangl.core import Entity, Registry, BehaviorRegistry
from tangl.core.behavior import DEFAULT_HANDLERS

# imported from tangl.__info__
DEFAULT_VARS = {'version': __version__}

# todo: demote vars to objects that work with vm and are collected by registered ns handlers

class Domain(Entity):
    """
    Domain(vars: dict[str, ~typing.Any], handlers: BehaviorRegistry)

    Bundle of capabilities: variables + handlers.

    Why
    ----
    A domain publishes a coherent namespace of identifiers and functions.
    Domains can represent story rules, environmental constraints, or character
    abilities. They can be affiliated (explicit, opt-in) or structural (implicit,
    inferred from graph).

    API
    ---
    - :attr:`locals` – shared identifiers/values
    - :attr:`handlers` – registry of callable behaviors
    - :meth:`add_vars`, :meth:`add_handler`, :meth:`register_handler`
    """
    locals: StringMap = Field(default_factory=dict)
    handlers: BehaviorRegistry = Field(default_factory=BehaviorRegistry)

    # delegated decorator
    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)

# Type Alias
DomainRegistry = Registry[Domain]

global_domain = Domain(label="globals",
                       locals=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       )
