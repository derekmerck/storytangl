from typing import Any, Iterable, TypeAlias
from collections import ChainMap

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.registry import Registry
from tangl.core.graph import Node
from tangl.core.dispatch import HandlerRegistry, DEFAULT_HANDLERS


try:
    from tangl.info import __version__
except ImportError:
    # In case info doesn't exist
    __version__ = '3.x'

DEFAULT_VARS = {'version': __version__}


class Domain(Entity):
    # Domains are collections of sharable identifiers, handlers,
    # provisioners that can be aggregated into a scope.
    #
    # Domains may be explicitly adopted, often as a singleton with a
    # label- or type-based opt-in, or implicitly assigned by membership
    # in a group, such as a subgraph that donates capabilities to its
    # members.
    #
    # Capabilities:
    # - shared vars
    # - shared handlers
    # - shared providers

    vars: StringMap = Field(default_factory=dict)
    handlers: HandlerRegistry = Field(default_factory=HandlerRegistry)
    # providers: list[Provider] = Field(default_factory=list)

    def add_vars(self, vars: dict[str, Any]) -> None:
        self.vars.update(vars)

    def add_handler(self, func, **attrs) -> None:
        self.handlers.add(func, **attrs)

    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)

    # def add_provider(self, provider: Provider) -> None:
    #     self.providers.append(provider)

class DomainRegistry(Registry[Domain]):
    # I'm not sure how this should be organized:
    # - a single global registry
    # - a singleton Domain class where every domain is named and findable in the _instances registry?
    # - A list of multiple registries per type and story world?

    def find_domains_for(self, node: Node) -> Iterable[Domain]:
        # check tags, class type for matching domains in self
        return ()

# Not needed yet
# class SingletonDomain(Domain, Singleton):
#     # indicated explicitly by tags or type/class membership
#     ...

global_domain = Domain(label="globals",
                       vars=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       )
