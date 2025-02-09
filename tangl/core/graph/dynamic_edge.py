from __future__ import annotations
from typing import Generic, TypeVar
from uuid import UUID

from tangl.type_hints import StringMap, Expr, UniqueLabel
from .graph import Node, Edge

NodeT = TypeVar("NodeT", bound=Node)

class DynamicEdge(Edge, Generic[NodeT]):
    """
    An edge with a lazily-linked successor.  Successor may be referenced by name,
    found by criteria, or created from a template when needed.
    """
    successor_ref: UniqueLabel = None  # node label/path in the graph
    successor_template: StringMap = None
    successor_criteria: StringMap = None
    # with current framework, id could just be criteria alias=abc, and a single key/empty val criteria could just become {alias=key}, although then it's not always guaranteed to exist

    def _dynamic_link_successor(self) -> NodeT:

        if self.successor_ref:
            # this _must_ succeed if a ref_id is given explicitly (when lazily evaluated)
            return self.graph.find_one(alias=self.successor_ref)
        elif self.successor_template:
            # this _must_ succeed if a template is given explicitly
            successor = NodeT.structure(**self.successor_template)
            # todo: don't forget to call on_create hook, or get this from the script manager?
            self.graph.add(successor)
            return successor
        elif self.successor_conditions:
            # this need not succeed, returning None will simply leave this link unavailable
            return self.graph.find_one(conditions=self.successor_conditions)

    def successor(self) -> NodeT:
        if self.successor_id is None:
            if x := self._dynamic_link_successor():
                self.successor_id = x.uid
        return super().successor.fget()
