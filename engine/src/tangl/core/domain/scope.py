# Scope is a node-anchored view of all relevant affiliate and structured domains.

from typing import Any, Iterator, TypeAlias
from functools import cached_property
from collections import ChainMap
import itertools
from uuid import UUID

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Graph, Node
from tangl.core.registry import Registry
from tangl.core.dispatch import Handler
from .domain import Domain, global_domain

NS: TypeAlias = ChainMap[str, Any]

class Scope(Entity):
    # A scope is an ordered collection of domains that are accessible/can influence
    # an anchor node.  Domains may be explicitly affiliated or structurally inferred.

    graph: Graph = Field(default_factory=Graph)
    # Has a graph, but is not a graph item, per se
    anchor_id: UUID = None
    domain_registry: Registry[Domain] = Field(default_factory=Registry)

    @property
    def anchor(self) -> Node:
        return self.graph.get(self.anchor_id)

    def _iter_active_domains(self) -> Iterator[Domain]:
        seen = set()

        # 1) structural (anchor -> nearest ancestors)
        for sg in [self.anchor, *self.anchor.ancestors()]:
            for d in self.domain_registry.find_domains_for(sg):
                if d.uid not in seen:
                    seen.add(d.uid)
                    yield d

        # 2) anything selected directly for the anchor
        for d in self.domain_registry.find_domains_for(self.anchor):
            if d.uid not in seen:
                seen.add(d.uid)
                yield d

        # 3) always include globals, last
        if global_domain.uid not in seen:
            seen.add(global_domain.uid)  # irrelevant but included for completeness
            yield global_domain

    @cached_property
    def active_domains(self) -> list[Domain]:
        return list(self._iter_active_domains())

    @classmethod
    def merge_vars(cls, *members, **criteria) -> NS:
        # closest to farthest
        maps = ( m.vars for m in members if m.matches(**criteria) )
        return ChainMap(*maps)

    @cached_property
    def namespace(self) -> NS:
        return self.merge_vars(*self.active_domains)

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        return Registry.chain_find_all(*(d.handlers for d in self.active_domains), **criteria)
