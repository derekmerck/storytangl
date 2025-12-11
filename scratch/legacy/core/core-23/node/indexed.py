from __future__ import annotations
from typing import Optional

import pluggy

from .index import Index

import attr
from .tree import TreeMixin

@attr.s(slots=False)
class IndexedTreeMixin(TreeMixin):
    """
    IndexedTreeMixin enhances nodes by providing functionalities related to their association
    with an Index. It ensures nodes are aware of their belonging to an index and offers utility
    methods to interact with the index.

    Features:
    - Equips nodes with awareness of their association to an index.
    - Ensures data integrity by allowing only root nodes to hold a direct reference to an index.
    - Provides nodes access to the index and potentially a plugin manager for extensibility.
    - Automatically adds nodes to their associated index upon initialization.

    Note:
    This mixin acts as a bridge between individual nodes and the Index, ensuring a structured
    and organized relationship.
    """

    # Def registered
    _index: Optional[Index] = attr.ib( eq=False, repr=False )

    @_index.validator
    def _val_index(self, attrib, value):
        if self.parent and value:
            raise ValueError("Only root nodes need to hold an index")

    @_index.default
    def _mk_index(self):
        if not self.parent:
            return Index()

    @property
    def index(self) -> Index:
        return self.root._index

    @TreeMixin.parent.setter
    def parent(self, value):
        TreeMixin.parent.fset(self, value)
        if self._parent is not None:
            self._index = None
            # recursively add self and any children
            self.index.add(self)

    @property
    def pm(self) -> Optional[pluggy.PluginManager]:
        return self.index.pm

    # Finalize
    def __attrs_post_init__(self):
        try:
            super().__attrs_post_init__()
        except AttributeError:
            pass
        self.index.add(self)
        if self.pm is not None:
            self.pm.hook.on_init_node(node=self)
