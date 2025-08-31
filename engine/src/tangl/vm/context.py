# tangl/vm/context.py
from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID
import functools
from dataclasses import dataclass, field

from tangl.type_hints import Step
from tangl.core.graph import Graph, Node
from tangl.core.domain import Scope, NS, DomainRegistry
from tangl.core.handler import Handler
from tangl.core.provision import Provider

# dataclass for simplified init, not serialized or tracked
@dataclass
class Context:
    # All the working vars for a step on the graph
    graph: Graph
    cursor_id: UUID
    step: Step = -1
    domain_registry: DomainRegistry = field(default_factory=DomainRegistry)

    @property
    def cursor(self):
        if self.cursor_id not in self.graph:
            raise RuntimeError(f"Bad cursor id in context {self.cursor_id} not in {[k for k in self.graph.keys()]}")
        return self.graph.get(self.cursor_id)

    @cursor.setter
    def cursor(self, value: UUID | Node):
        if isinstance(value, UUID):
            pass
        elif isinstance(value, Node):
            value = value.uid
        else:
            raise TypeError(f"Invalid cursor type {type(value)}")
        self.cursor_id = value
        if self.cursor_id not in self.graph:
            raise RuntimeError(f"Bad cursor id in context {self.cursor_id}")
        self._invalidate_scope()

    @functools.cached_property
    def scope(self) -> Scope:
        return Scope(graph=self.graph,
                     anchor_id=self.cursor_id,
                     domain_registry=self.domain_registry)

    def _invalidate_scope(self):
        if hasattr(self, "scope"):
            del self.scope

    def get_ns(self) -> NS:
        ns = self.scope.namespace
        # The context is, itself a domain layer
        context_layer = {'cursor': self.cursor, 'step': self.step}
        return ns.new_child(context_layer)

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        return self.scope.get_handlers(**criteria)

    def get_providers(self, **criteria) -> Iterator[Provider]:
        return self.scope.get_providers(**criteria)
