from __future__ import annotations
from typing import Self, Any, Literal

from scipy.optimize import anderson

# noinspection PyUnresolvedReferences
from ..graph import Node, Graph
from ..handler_pipeline import HandlerPipeline, PipelineStrategy

on_can_associate = HandlerPipeline[Node, bool]("on_can_associate", pipeline_strategy=PipelineStrategy.ALL)
on_can_disassociate = HandlerPipeline[Node, bool]("on_can_disassociate", pipeline_strategy=PipelineStrategy.ALL)
on_associate = HandlerPipeline[Node, Any]("on_associate")
on_disassociate = HandlerPipeline[Node, Any]("on_disassociate")

Relationship = Literal['as_parent', 'as_child', 'as_peer']

class Associating(Node):
    """
    A Node that can form parent/child or peer relationships with other nodes.

    Parent/child relationships are hierarchical, while peer relationships allow
    bidirectional linking without hierarchy.
    """

    @property
    def associates(self) -> list[Self]:
        """Get all nodes this node is associated with"""
        return self.find_children(has_cls=Associating)

    @on_can_associate.register()
    def _return_true(self, *, other: Self, relationship: Relationship, **context) -> Any:
        return True

    @on_can_disassociate.register()
    def _return_true(self, *, other: Self, **context) -> Any:
        return True

    @on_associate.register()
    def _add_other_as_child(self, *, other: Self, relationship: Relationship, **context):
        match relationship:
            case "as_parent":
                self.add_child(other)
            case "as_peer":
                self.add_child(other, as_parent=False)
            case "as_child":
                # Association is handled by the parent side
                pass

    # # @on_associate.register()
    # def _call_other_associate(self, *, other: Self, relationship: Relationship, depth: int = 0, **context):
    #     """Ensures mutual association without infinite recursion."""
    #     if depth > 1:  # Prevent infinite loops
    #         return
    #     match relationship:
    #         case "as_parent":
    #             other.associate_with(other=self, relationship="as_child", depth=depth+1, **context)
    #         case "as_child":
    #             other.associate_with(other=self, relationship="as_parent", depth=depth+1, **context)
    #         case "as_peer":
    #             other.associate_with(other=self, relationship="as_peer", depth=depth+1, **context)

    @on_disassociate.register()
    def _remove_other_as_child(self, *, other: Self, **context):
        self.remove_child(other)  # This fails quietly if not a child

    # # @on_disassociate.register()
    # def _call_other_disassociate(self, *, other: Self, depth: int = 0, **context):
    #     """Ensures mutual disassociation without infinite recursion."""
    #     if depth > 1:  # Prevent infinite loops
    #         return
    #     other.disassociate_from(other=self, depth=depth + 1, **context)

    @classmethod
    def _validate_relationship(cls, relationship: Relationship):
        """Validate relationship type"""
        valid = ('as_parent', 'as_child', 'as_peer')
        if relationship not in valid:
            raise ValueError(f"Invalid relationship: {relationship}. Must be one of {valid}")

    @classmethod
    def _inv_relationship(cls, relationship: Relationship):
        """Validate relationship type"""
        match relationship:
            case "as_parent":
                return "as_child"
            case "as_child":
                return "as_parent"
            case "as_peer":
                return "as_peer"
        valid = ('as_parent', 'as_child', 'as_peer')
        raise ValueError(f"Invalid relationship: {relationship}. Must be one of {valid}")

    def can_associate_with(self, *, other: Self, relationship: Relationship = "as_peer", **context):
        """
        Check if association is allowed

        Args:
            other: Node to potentially associate with
            relationship: Type of relationship to form
            **context: Additional context for handlers

        Returns:
            bool: True if association is allowed
        """
        self._validate_relationship(relationship)
        inv_relationship = self._inv_relationship(relationship)
        return on_can_associate.execute(self, other=other, relationship=relationship, **context) and \
            on_can_associate.execute(other, other=self, relationship=inv_relationship, **context)

    def can_disassociate_from(self, *, other: Self, **context):
        """
        Check if disassociation is allowed

        Args:
            other: Node to potentially disassociate from
            **context: Additional context for handlers

        Returns:
            bool: True if disassociation is allowed
        """
        return on_can_disassociate.execute(self, other=other, **context) and \
            on_can_disassociate.execute(other, other=self, **context)

    def associate_with(self, *, other: Self, relationship: Relationship = "as_peer", **context):
        """
        Form an association with another node

        Args:
            other: Node to associate with
            relationship: Type of relationship to form
            **context: Additional context for handlers

        Raises:
            ValueError: If relationship type is invalid
            RecursionError: If circular association is detected
        """
        self._validate_relationship(relationship)
        inv_relationship = self._inv_relationship(relationship)

        if not self.can_associate_with(other=other, relationship=relationship, **context):
            raise ValueError(f"Cannot associate {self} with {other}")

        if other.uid in self.children_ids:
            # already associated, cannot double associate
            return

        on_associate.execute(self, other=other, relationship=relationship, **context)
        on_associate.execute(other, other=self, relationship=inv_relationship, **context)

    def disassociate_from(self, *, other: Self, **context):
        """
        Remove an association with another node

        Args:
            other: Node to disassociate from
            **context: Additional context for handlers
        """
        if not self.can_disassociate_from(other=other, **context):
            raise ValueError(f"Cannot disassociate {self} from {other}")
        on_disassociate.execute(self, other=other, **context)
        on_disassociate.execute(other, other=self, **context)
