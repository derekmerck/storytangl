# tangl/core/domain/scope.py
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
    Scope(domains: Registry[Domain], graph: Graph, anchor: Node)

    Ordered stack of active domains for a node.

    Why
    ----
    Determines *what is visible and effective* from a given anchor in the graph.
    Combines structural domains (ancestors) and affiliate domains (opt-in).

    Key Features
    ------------
    * **Namespace** – merge of all domain vars, nearest-first.
    * **Handlers** – aggregate handler registries into a unified pipeline.

    API
    ---
    - :attr:`active_domains` – list of active domains given the anchor, graph, and domain registries available
    - :attr:`namespace` – merged :class:`~python:collections.ChainMap`
    - :meth:`get_handlers` – yield applicable handlers
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

        # order as [ anchor -> nearest ancestors -> graph ]
        items = [anchor, *getattr(anchor, "ancestors", lambda: [])(), anchor.graph]

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
        return Registry.chain_find_all(
            *(d.handlers for d in self.active_domains),
            **criteria,
            sort_key=lambda x: (x.priority, x.seq),
        )

    def find_all(self, **criteria) -> Iterator[GraphItem]:
        """Proxy :meth:`Graph.find_all` through the scope's graph."""

        return self.graph.find_all(**criteria)
