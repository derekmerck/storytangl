from __future__ import annotations
from typing import Generic, TypeVar, Optional
import logging

from pydantic import model_validator

from tangl.type_hints import StringMap, UniqueLabel, Identifier
from tangl.core import Entity
from .node import Node
from .edge import Edge

logger = logging.getLogger(__name__)

SuccessorT = TypeVar("SuccessorT", bound=Entity)

class DynamicEdge(Edge[SuccessorT], Generic[SuccessorT]):
    """
    An edge with a lazily-linked successor.  Successor may be referenced by name,
    found by criteria, or created from a template when needed.
    """
    successor_ref: Identifier = None  # node label/path in the graph
    successor_template: StringMap = None
    successor_criteria: StringMap = None

    # Do we still need this?
    # successor_conditions: Strings = None

    @model_validator(mode='after')
    def _validate_has_link_method(self):
        """
        Ensure at least one linking method is specified

        If no linking directive is provided, defaults to using the label as the with ref.
        """
        if not self.successor:
            methods = [self.successor_ref, self.successor_template, self.successor_criteria]
            logger.debug([self.successor_ref, self.successor_template, self.successor_criteria])
            if not any(methods):
                # if self.label is not None:
                #    self.successor_ref = self.label
                # todo: Ensure we use the _raw_ label (link-label may already be assigned, never _None_)
                raise ValueError("Must specify either successor ref, template or criteria")
        return self

    def _resolve_by_ref(self) -> Optional[SuccessorT]:
        """Find successor by reference"""
        return self.graph.find_one(alias=self.successor_ref)

    def _resolve_by_template(self) -> Optional[SuccessorT]:
        """Create successor from template"""
        # todo: set correct class!
        successor = Node.structure(self.successor_template)
        self.graph.add(successor)
        return successor

    def _resolve_by_criteria(self) -> Optional[SuccessorT]:
        """Find successor by search criteria"""
        return self.graph.find_one(**self.successor_criteria)

    def _resolve_successor(self) -> Optional[SuccessorT]:
        """Attempt to resolve successor through available methods"""
        if self.successor_ref:
            return self._resolve_by_ref()
        elif self.successor_template:
            return self._resolve_by_template()
        elif self.successor_criteria:
            return self._resolve_by_criteria()
        return None

    def clear_successor(self):
        """Explicitly clear the cached successor"""
        self.successor_id = None

    @property
    def successor(self) -> Optional[SuccessorT]:
        """Get or resolve the successor node"""
        if self.successor_id is None:
            if successor := self._resolve_successor():
                # successor_id is cached
                self.successor_id = successor.uid
        return super().successor
