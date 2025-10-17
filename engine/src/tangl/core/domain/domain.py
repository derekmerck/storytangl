# tangl/core/domain/domain.py
from typing import Any

from pydantic import Field

from tangl.info import __version__
from tangl.type_hints import StringMap
from tangl.core import Entity, Registry, DispatchRegistry
from tangl.core.dispatch import DEFAULT_HANDLERS

# imported from tangl.__info__
DEFAULT_VARS = {'version': __version__}

class Domain(Entity):
    """
    Domain(vars: dict[str, ~typing.Any], handlers: DispatchRegistry)

    Bundle of capabilities: variables + handlers.

    Why
    ----
    A domain publishes a coherent namespace of identifiers and functions.
    Domains can represent story rules, environmental constraints, or character
    abilities. They can be affiliated (explicit, opt-in) or structural (implicit,
    inferred from graph).

    API
    ---
    - :attr:`vars` – shared identifiers/values
    - :attr:`handlers` – registry of callable behaviors
    - :meth:`add_vars`, :meth:`add_handler`, :meth:`register_handler`
    """
    vars: StringMap = Field(default_factory=dict)
    handlers: DispatchRegistry = Field(default_factory=DispatchRegistry)

    def add_vars(self, vars: dict[str, Any]) -> None:
        self.vars.update(vars)

    def get_vars(self) -> StringMap:
        return self.vars

    def add_handler(self, func, **attrs) -> None:
        self.handlers.add(func, **attrs)

    # delegated decorator
    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

DomainRegistry = Registry[Domain]

global_domain = Domain(label="globals",
                       vars=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       )

# @global_domain.handlers.register(priority=100, job="namespace", is_instance=Domain)
# def _include_vars_in_ns(inst: Domain, *_, **__) -> StringMap:
#     if inst.vars:
#         return inst.vars

