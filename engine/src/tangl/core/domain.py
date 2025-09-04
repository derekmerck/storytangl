
from typing import Any, Iterator, Self, Iterable
import functools
from collections import ChainMap
import itertools
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from .entity import Entity, Registry
from .graph import Graph, Node
from .handler import Handler, HandlerRegistry, DEFAULT_HANDLERS
from .provision import Provider, DEFAULT_PROVISIONERS

NS = ChainMap[str, Any]

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
    providers: list[Provider] = Field(default_factory=list)

    def add_vars(self, vars: dict[str, Any]) -> None:
        self.vars.update(vars)

    def add_handler(self, func, **attrs) -> None:
        self.handlers.add(func, **attrs)

    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)

    def add_provider(self, provider: Provider) -> None:
        self.providers.append(provider)

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

# put generic finder/generic builder in here for provisioning
global_domain = Domain(label="globals",
                       vars=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       providers=DEFAULT_PROVISIONERS)

class Scope(Entity):

    graph: Graph = Field(default_factory=Graph)
    anchor_id: UUID = None
    domain_registry: Registry[Domain] = Field(default_factory=Registry)

    @property
    def anchor(self) -> Node:
        return self.graph.get(self.anchor_id)

    @functools.cached_property
    def active_domains(self) -> Iterator[Domain]:
        seen = set()
        for d in self.domain_registry.find_domains_for(self.anchor):
            if d.uid not in seen:
                seen.add(d.uid)
                yield d
        for ancestor in self.anchor.ancestors():
            for d in self.domain_registry.find_domains_for(ancestor):
                if d.uid not in seen:
                    seen.add(d.uid)
                    yield d
        if global_domain.uid not in seen:
            seen.add(global_domain.uid)  # irrelevant but included for completeness
            yield global_domain

    @classmethod
    def merge_vars(cls, *members, **criteria) -> NS:
        # closest to farthest
        maps = ( m.vars for m in members if m.matches(**criteria) )
        return ChainMap(*maps)

    @functools.cached_property
    def namespace(self) -> NS:
        return self.merge_vars(*self.active_domains)

    @classmethod
    def merge_handlers(cls, *members, **criteria) -> Iterator[Handler]:
        handlers = ( m.handlers for m in members if m.matches(**criteria) )
        yield from itertools.chain(*handlers)

    # todo: do we want to include general predicates here?
    def get_handlers(self, **criteria) -> Iterator[Handler]:
        return self.merge_handlers(*self.active_domains, **criteria)

    @classmethod
    def merge_providers(cls, *members, **criteria) -> Iterator[Provider]:
        providers = (m.providers for m in members if m.matches(**criteria))
        yield from itertools.chain(*providers)

    # todo: do we want to include general predicates here?
    def get_providers(self, **criteria) -> Iterator[Provider]:
        return self.merge_providers(*self.active_domains, **criteria)
