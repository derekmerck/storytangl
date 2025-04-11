"""
Nodes can be associated in several ways:

- Directly through parent/child relationships.  These relationships can be added programmatically with "add_child()" and "remove_child".  No edge is required.
- For direct parent/child relationships, the child node is added to the parent's children.
- For direct peer relationships, neither node is the parent of the other, both nodes are added to the other's children.

- Indirectly through an 'edge', where one node is the predecessor and the other is the successor.
- Simple Edges have no parent/child relationships with the graph, and can be garbage collected.
- Normal Edges have parent-only relationships and reference their successor as a named field.
- Dynamic Edges have parent-only relationships UNTIL they are dereferenced, at which point they can attach to an already existing node by name or conditions, or even create a new node _de novo_.

Both direct and indirect relationships may be _mutable_.  In such cases, nodes are either temporarily related as parent/child (ownership or assignment) or peer-to-peer (connected).  For indirect relationships (Dynamic Edges), the association is between the edge itself and the successor node.

Managing such mutable associations and transactions requires additional flexibility, so they are managed through an AssociationHandler.
"""

from __future__ import annotations
from typing import Optional, Protocol, Literal
from uuid import UUID

import logging

from pydantic import Field, model_validator

from tangl.core.entity import Entity
from .node import Node

logger = logging.getLogger(__name__)

class EdgeProtocol(Protocol):
    predecessor: Entity
    successor: Entity


class SimpleEdge(Entity):
    """
    An SimpleEdge is an *anonymous* (unregistered) link between two entities. The entities
    themselves do not hold links to the edge, so the connector can be garbage collected.
    """
    predecessor: Entity
    successor: Entity

    def __repr__(self):
        s = f"<{type(self).__name__}:{self.predecessor.label}->{self.successor.label}>"
        return s


class Edge(Node):
    """
    An Edge is a specialized :class:`~tangl.core.graph.Node` that connects a parent predecessor node
    with a linked successor node, facilitating traversal and story flow.

    Key Features
    ------------
    * **Predecessor-Successor Relationship**: Links two nodes for traversal purposes.
    * **Predecessor Child**: Edges are typically created as children of their predecessor nodes.

    Usage
    -----
    .. code-block:: python

        from tangl.core.graph import Node, Edge

        # Create nodes and an edge
        predecessor = Node(label="start")
        successor = Node(label="next")
        edge = Edge(predecessor=predecessor, successor=successor)

        # Access edge properties
        print(edge.predecessor == predecessor)  # True
        print(edge.successor == successor)  # True
    """
    parent_id: UUID = Field(..., alias="predecessor_id")  # required now

    @model_validator(mode='before')
    @classmethod
    def _alias_predecessor_to_parent(cls, data):
        if predecessor := data.pop('predecessor', None):
            data.setdefault("predecessor_id", predecessor.uid)
            if predecessor.graph is not None:
                data.setdefault('graph', predecessor.graph)
        return data

    # todo: what is the pydantic attribute property markup so this shows up as an allowable input in the schema?
    @property
    def predecessor(self) -> Node:
        return self.parent

    successor_id: UUID = None

    @model_validator(mode='before')
    @classmethod
    def _reference_successor(cls, data):
        if successor := data.pop('successor', None):
            data.setdefault("successor_id", successor.uid)
            if successor.graph is not None:
                data.setdefault('graph', successor.graph)
        return data

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id, None)

    @successor.setter
    def successor(self, value: UUID | Node):
        if value:
            if isinstance(value, UUID):
                self.successor_id = value
            elif isinstance(value, Node):
                self.successor_id = value.uid

    # todo: add this to on avail handler for edges
    # @on_avail.strategy("on_available")
    # def _check_successor_avail(self, **kwargs) -> bool:
    #     if hasattr(self.successor, "available"):
    #         return self.successor.available()

    def __repr__(self):
        try:
            successor_label = self.successor.label
        except (KeyError, AttributeError, TypeError):
            successor_label = self.successor_id
        try:
            predecessor_label = self.predecessor.label
        except (KeyError, AttributeError, TypeError):
            predecessor_label = "anon"
        s = f"<{type(self).__name__}:{predecessor_label}->{successor_label}>"
        return s
