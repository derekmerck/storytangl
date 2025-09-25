# tangl/vm/context.py
from __future__ import annotations
from typing import Iterator, Any
from uuid import UUID
import functools
from enum import Enum
from dataclasses import dataclass, field

# from tangl.core import JobReceipt
from tangl.core.graph import Graph, Node
from tangl.core.registry import Registry
from tangl.core.domain import Scope, NS, AffiliateDomain
from tangl.core.dispatch import Handler

# dataclass for simplified init and frozen, not serialized or tracked
@dataclass(frozen=True)
class Context:
    # All the working vars to create the 'scope' for a step on the graph

    # We don't want to mix context into the handler signature, we give handlers a
    # node or a namespace, they return a result, the Frame's job is to track that
    # via a context object, context is persistent across phases, although the graph itself
    # may be mutated or recreated

    graph: Graph
    cursor_id: UUID
    domain_registries: list[Registry[AffiliateDomain]] = field(default_factory=list)

    @property
    def cursor(self) -> Node:
        if self.cursor_id not in self.graph:
            raise RuntimeError(f"Bad cursor id in context {self.cursor_id} not in {[k for k in self.graph.keys()]}")
        return self.graph.get(self.cursor_id)

    @functools.cached_property
    def scope(self) -> Scope:
        # Since Context is frozen wrt the scope parts, we never need to invalidate this.
        return Scope(graph=self.graph,
                     anchor_id=self.cursor_id,
                     domain_registries=self.domain_registries)

    def inspect_scope(self) -> str:
        lines = ["Active domains:"]
        for d in self.scope.active_domains:
            lines.append(f" - {d.__class__.__name__}:{d.label or d.short_uid()}")
        lines.append("Handlers by phase:")
        for ph in P:
            names = [h.func.__name__ for h in self.scope.get_handlers(phase=ph)]
            lines.append(f"  {ph.name}: {', '.join(names)}")
        return "\n".join(lines)

    def get_ns(self) -> NS:
        return self.scope.namespace

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        # can pass phase in filter criteria if useful
        return self.scope.get_handlers(**criteria)
