# todo: traversable - implement `enter_and_return`, `exit_with_return`

from __future__ import annotations
from enum import Enum

import attr

from tangl.utils.enum_utils import EnumUtils
from .renderable import RenderableMixin
from .runtime import RuntimeMixin

class AutoTraverse( EnumUtils, Enum ):
    NONE = "none"
    ON_ENTER = "on_enter"
    ON_EXIT = "on_exit"


@attr.s
class TraversableMixin(RenderableMixin, RuntimeMixin):
    """
    Mixin class to add traversability attributes to a node.

    Enhances a node with the ability to be entered, exited, and to track its traversal history.

    Attributes:
        - visited: List of times the node was accessed.
        - repeats: Boolean indicating if a node can be revisited after its initial access.

    Properties:
        - turns_since: Returns the turns since the last time the node was visited.
        - num_visits: Provides the total number of times the node was visited.
        - completed: Indicates if the node has been accessed and if it can be revisited.

    Methods:
        - is_enterable: Determines if the node's entry conditions are met.
        - enter: Applies effects and registers the entry.
        - exit: Logic for exiting the node and determining the next node.

    Notes:
        - Inherits from RenderableMixin and RuntimeMixin for additional functionality.
        - Utilizes plugin hooks to allow custom behavior on entry and exit.
    """
    visited: list[int] = attr.ib(factory=list)

    @property
    def turns_since(self) -> int:
        if not self.visited:
            return -1
        if self.index and hasattr(self.index, 'turn'):
            current_turn = self.index.turn
            return current_turn - self.visited[-1]
        return -1

    @property
    def num_visits(self):
        return len( self.visited )

    repeats: bool = False

    @property
    def completed(self):
        return not self.repeats and len(self.visited) > 0

    def is_enterable(self, force=False) -> bool:
        """Returns True if the block's conditions are satisfied, else False."""
        return self.is_satisfied(force=force)

    def enter(self, force=False) -> TraversableMixin:
        """Apply the node's effects and return a pointer to the current node."""
        if not self.is_enterable(force=force):
            raise Exception("Cannot enter node - entry conditions not met.")
        if self.index and hasattr(self.index, 'turn'):
            self.visited.append( self.index.turn )
        if hasattr(self, "pm") and self.pm is not None:
            nodes = self.pm.hook.on_enter_node(node=self)
            if nodes and nodes[0] is not self:
                return nodes[0].enter()
        self.apply_effects()
        return self

    def exit(self) -> TraversableMixin:
        """Should return the next node, which is dependent on the current node class."""
        if hasattr(self, "pm") and self.pm is not None:
            nodes = self.pm.hook.on_exit_node(node=self)
            if nodes and nodes[-1] is not self:
                return nodes[-1]
