# tangl/vm/context.py
from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID
import functools
from dataclasses import dataclass, field
import hashlib
from random import Random

from tangl.type_hints import Step
from tangl.core.graph import Graph, Node
from tangl.core.domain import Scope, DomainRegistry, NS
from tangl.core.dispatch import Handler
from ..utils.hashing import hashing_func

# dataclass for simplified init and frozen, not serialized or tracked
@dataclass(frozen=True)
class Context:
    # All the working vars for a step on the graph
    # We don't want to mix context into the handler signature, we give handlers a
    # node or a namespace, they return a result, the session's job is to track that
    # via a context object, context is persistent across phases, although the graph itself
    # may be mutated or recreated

    graph: Graph
    cursor_id: UUID
    epoch: Step = -1  # technically may not be necessary since it's tracked at session level?
    domain_registry: DomainRegistry = field(default_factory=DomainRegistry)

    @property
    def cursor(self) -> Node:
        if self.cursor_id not in self.graph:
            raise RuntimeError(f"Bad cursor id in context {self.cursor_id} not in {[k for k in self.graph.keys()]}")
        return self.graph.get(self.cursor_id)

    @functools.cached_property
    def rng(self):
        # Guarantees the same RNG sequence given the same context for deterministic replay
        # Since Context is frozen wrt the hash parts, we never need to invalidate this.
        h = hashing_func(self.graph.uid, self.epoch, self.cursor.uid, digest_size=8)
        seed = int.from_bytes(h, "big")
        return Random(seed)
        # todo: should injecting rng into the ns be a session level feature?

    @functools.cached_property
    def scope(self) -> Scope:
        # Since Context is frozen wrt the scope parts, we never need to invalidate this.
        return Scope(graph=self.graph,
                     anchor_id=self.cursor_id,
                     domain_registry=self.domain_registry)

    def get_ns(self) -> NS:
        ns = self.scope.namespace
        # The context is, itself, a domain layer
        context_layer = {
            'cursor': self.cursor,
            'epoch': self.epoch,
            'rng': self.rng}
        return ns.new_child(context_layer)

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        # can pass phase in filter criteria if useful
        return self.scope.get_handlers(**criteria)
