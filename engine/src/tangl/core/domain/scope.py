# tangl.core.scope.py
# Scope is a node-anchored view of all relevant affiliate and structured domains.
from typing import Any, Iterator, TypeAlias
from functools import cached_property
from collections import ChainMap
from uuid import UUID

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Graph, Node, GraphItem
from tangl.core.registry import Registry
from tangl.core.dispatch import Handler
from .domain import Domain, global_domain

NS: TypeAlias = ChainMap[str, Any]


class Scope(Entity):
    """
    A scope is a transient, ordered collection of domains that are accessible to or
    can influence an anchor node.

    Domains may be explicitly affiliated or structurally inferred.
    """

    graph: Graph = Field(..., exclude=True)
    # Has a graph, but Scope is not a graph item, per se
    anchor_id: UUID
    domain_registries: list[Registry[Domain]] = Field(default_factory=list)

    @property
    def anchor(self) -> Node:
        return self.graph.get(self.anchor_id)

    # Can't cache this directly b/c it only iterates once
    @classmethod
    def _iter_active_domains(cls, anchor: GraphItem, registries: list[Registry[Domain]]) -> Iterator[Domain]:
        # In general, I'm not sure how this should be organized:
        """
        Yield registered domains whose tags intersect item/ancestor tags or whose selector returns True.

        Uses 'domain:{label} tag and class type for matching affiliates by default.
        Includes ancestors when they are of type "StructuralDomain"
        """

        seen: set[UUID] = set()

        def new_domain(domain_: Domain):
            nonlocal seen
            if domain_.uid not in seen:
                seen.add(domain_.uid)
                return True
            return False

        # order as [ anchor -> nearest ancestors ]
        items = [anchor, *getattr(anchor, "ancestors", lambda: [])()]

        for item in items:
            # 1) Include structural domain ancestors
            if isinstance(item, Domain) and new_domain(item):
                # Include the item directly if it is a domain (e.g., scene, book)
                yield item
            # 2) Include affiliates of the anchor and each ancestor
            for registry in registries:
                for domain in registry.select_for(item):
                    if new_domain(domain):
                        yield domain

        # 3) always include globals, last
        if new_domain(global_domain):
            yield global_domain

    @cached_property
    def active_domains(self) -> list[Domain]:
        return list(self._iter_active_domains(self.anchor, self.domain_registries))

    @classmethod
    def merge_vars(cls, *members: Domain, **criteria) -> NS:
        # closest to farthest
        maps = ( m.vars for m in members if m.matches(**criteria) )
        return ChainMap(*maps)

    @cached_property
    def namespace(self) -> NS:
        return self.merge_vars(*self.active_domains)

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        return Registry.chain_find_all(*(d.handlers for d in self.active_domains), **criteria)
