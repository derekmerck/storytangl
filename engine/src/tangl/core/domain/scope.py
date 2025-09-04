# Scope is a node-anchored view of all relevant affiliate and structured domains.

from typing import Any, Iterator, Self, Iterable
import functools
from collections import ChainMap
import itertools
from uuid import UUID

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Graph, Node
from tangl.core.registry import Registry
from tangl.core.dispatch import Handler
from .domain import Domain, global_domain, NS

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

    # @classmethod
    # def merge_providers(cls, *members, **criteria) -> Iterator[Provider]:
    #     providers = (m.providers for m in members if m.matches(**criteria))
    #     yield from itertools.chain(*providers)
    #
    # # todo: do we want to include general predicates here?
    # def get_providers(self, **criteria) -> Iterator[Provider]:
    #     return self.merge_providers(*self.active_domains, **criteria)
