from __future__ import annotations
from typing import Optional
from uuid import UUID

import attr

from .unique_id import UniqueIdMixin

@attr.s(slots=False)
class TreeMixin(UniqueIdMixin):
    """
    Provides functionalities related to tree structures, enabling a node to be aware of its position
    within the tree and access its parent and children.

    Attributes:
        _parent: The parent of the current node. Defaults to `None` for root nodes.
        children: A dictionary holding child nodes.

    Properties:
        parent: Accessor for the `_parent` attribute.
        path: Returns the path from the root to the current node, using the node's unique ID (`uid`).
        root: Returns the root node by traversing the tree upwards.

    Methods:
        get_child(guid): Retrieves a child node based on its `guid`.
        add_child(child): Adds a child node and sets the current node as its parent.
        remove_child(child): Removes a child node from the current node.

    Note:
        Ensure proper error handling when adding or removing children to avoid unexpected behaviors.
    """

    # Is tree
    _parent: Optional[TreeMixin] = attr.ib(
        default=None,
        eq = lambda x: x.guid if x else None,
        repr = lambda x: x.guid if x else None)

    @property
    def parent(self) -> Optional[TreeMixin]:
        # this is only a property so that it can have a setter
        return self._parent

    @parent.setter
    def parent(self, node: TreeMixin):
        self._parent = node

    @property
    def path(self) -> str:
        node = self
        s = self.uid
        while node.parent is not None:
            node = node.parent
            s = node.uid + "/" + s
        return s

    @property
    def root(self) -> Optional[TreeMixin]:
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    # Has children
    children: dict[UUID, TreeMixin] = attr.ib( factory=dict )

    def get_child(self, guid: UUID) -> TreeMixin:
        return self.children[guid]

    # Define methods to add and remove children
    def add_child(self, child: TreeMixin):
        child.parent = self
        self.children[child.guid] = child

    def remove_child(self, child: TreeMixin):
        del self.children[child.guid]