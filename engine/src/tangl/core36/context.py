from __future__ import annotations
from functools import cached_property
from uuid import UUID
from typing import Any, Self
from dataclasses import dataclass, field
from collections import ChainMap
from enum import Enum, auto

from tangl.type_hints import StringMap
from .entity import Entity
from .scope import Scope, ServiceName
from .graph import Graph

# Context Manager

# For re-play, there are only 3 atomic mutations:
class GraphOp(Enum):
    SET_VALUE = auto()
    ADD_ELEMENT = auto()
    REMOVE_ELEMENT = auto()

class Context:
    """
    A context is a wrapper around a graph that provides a list of
    currently active scopes, given the cursor position, and accessors
    to the basic operations: get, find, set, add, and remove for data,
    shape, and behavior.
    """
    graph: Graph
    user: Entity
    scopes: list[Scope] = field(default_factory=list)
    # build on demand: cursor -> parent(s) -> graph -> domain(s) -> global

    @cached_property
    def namespace(self) -> StringMap:
        ns_maps = []
        for s in self.scopes:
            if hasattr(s, "state"):
                ns_maps.append(s.state)
            if hasattr(s, "nodes"):
                nodes_by_path = { n.path for n in s.nodes }
                ns_maps.append(nodes_by_path)
        return ChainMap(*ns_maps)

        # todo: could attach a setter listener to locals and dataclass fields that
        #       emits patches to ctx.patch_stream
        #       similarly, could emit frags to ctx.frag_stream or any subscribers
        #       need to catch setting entity vars too, though, like cursor, successor

    # -------- Read API -------
    def get_value(self, key) -> Any:
        return self.namespace.get(key)

    def get_element(self, key):
        for s in self.scopes:
            if ( el := s.get_element(key) ) is not None:
                return el

    def find_behaviors_for(self, service: ServiceName):
        behaviors = []
        for s in self.scopes:
            behaviors.extend(s.find_behaviors(service, self.graph.cursor))
        return behaviors

    # -------- Invoke a behavior chain -----
    # todo: do we want this or do we want to capture all of the side-effects (write, add, remove)?
    #       I think we _log_ this but don't use it for replay, replay is just the side effect updates.
    def do_behavior(self, service: ServiceName, el: Element) -> 'BehaviorReceipt':
        behaviors = self.find_behaviors_for(service, el)
        results = []
        for b in behaviors:
            result = b.func(self.graph.cursor, self.namespace)
            results.append(result)
        # todo: aggregation/compose strategy
        return results

    # -------- Atomic Read/Write API -------
    # need directive -- in locals/shadow or where defined
    def set_value(self, key, value, scope: Scope = None) -> Patch:
        scope = scope or self._find_scope_for_key(key)
        scope.set_value(key, value)
        patch = Patch(
            scope_id=scope.uid,
            op=GraphOp.SET_VALUE,
            key=key,
            value=value,
        )
        return patch

    def add_element(self, el: Element, scope: Scope = None) -> Patch:
        scope = scope or self._find_scope_for_el(el)
        scope.add_element(el)
        patch = Patch(
            scope_id=scope.uid,
            op=GraphOp.ADD_ELEMENT,
            value=el.unstructure(),
        )
        return patch

    def remove_element(self, el: Element, scope: Scope = None) -> Patch:
        scope = scope or self._find_scope_for_el(el)
        scope.remove_element(el)
        patch = Patch(
            scope_id=scope.uid,
            op=GraphOp.REMOVE_ELEMENT,
            key=el.uid
        )
        return patch

    # ------ Patch Replay API -------
    def apply_patch(self, patch: Patch) -> Self:
        scope = next( scope for scope in self.scopes if scope.uid == patch.scope_id )
        return patch.apply(scope)

    def apply_patches(self, patches: list[Patch]) -> Self:
        ctx = self
        for patch in patches:
            ctx = ctx.apply_patch(patch)
        return ctx

# Updating an element is setting a value on a scope

@dataclass(frozen=True, slots=True)
class Patch:
    uid: UUID = field(default_factory=UUID)
    op: GraphOp = None
    scope_id: UUID = None
    key: str | UUID = None
    value: Any = None

    def apply(self, scope: Scope):
        match self.op:
            case GraphOp.SET_VALUE:
                scope.set_value(self.key, self.value)
            case GraphOp.ADD_ELEMENT:
                el = Entity.structure(**self.value)
                scope.add_element(el)
            case GraphOp.REMOVE_ELEMENT:
                scope.remove_element(self.key)
            case _:
                raise NotImplementedError(f"{self.op} is not implemented")

