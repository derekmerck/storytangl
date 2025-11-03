from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING
from uuid import UUID
from enum import Enum

from pydantic import Field, model_validator

from .graph import GraphItem, Graph

if TYPE_CHECKING:
    from .node import Node

# todo: should be a registry b/c its a collection?  It's really a _view_ of a registry
#       just need to implement pass-through for get and have add() and values() refer
#       to a private member list
class Subgraph(GraphItem):
    """
    Subgraph(members: list[GraphItem], subgraph_type: str)

    Named grouping of graph items addressed by membership.

    Why
    ----
    Represents hierarchical structure (e.g., scene/block) without duplicating
    topology. Stores member ids only; resolution back to items is via the owner graph.

    Key Features
    ------------
    * **Typed** – optional :attr:`subgraph_type`.
    * **Membership** – :meth:`add_member`, :meth:`remove_member`, :meth:`has_member`.
    * **Scoped search** – :meth:`find_all` / :meth:`find_one` over current members.

    API
    ---
    - :attr:`member_ids` – list of UUIDs; see :meth:`members` to iterate live items.
    - :meth:`members` – yields items by resolving ids through :class:`Graph.get`.
    - :meth:`add_member` – validates same-graph and updates cached parent on items.
    - :meth:`remove_member` – remove by item or UUID and invalidate cached parent.
    - :meth:`find_all` / :meth:`find_one` – criteria-based search among members.
    """
    subgraph_type: Optional[ str | Enum ] = None  # No need to enumerate this yet
    member_ids: list[UUID] = Field(default_factory=list)

    @property
    def members(self) -> Iterator[GraphItem]:
        for member_id in self.member_ids:
            member = self.graph.get(member_id)
            if member is not None:
                yield member

    def has_member(self, node: Node) -> bool:
        return node.uid in self.member_ids

    def add_member(self, item: GraphItem) -> None:
        self.graph._validate_linkable(item)
        if item.parent and item.parent is not self:
            item.parent.remove_member(item)
        self.member_ids.append(item.uid)
        item._invalidate_parent_attr()

    def remove_member(self, item: GraphItem | UUID):
        if isinstance(item, UUID):
            key = item
            item = self.graph.get(key)
        elif isinstance(item, GraphItem):
            key = item.uid
        else:
            raise TypeError(f"Expected UUID or GraphItem, got {type(item)}")
        item._invalidate_parent_attr()
        self.member_ids.remove(key)

    def find_all(self, **criteria) -> Iterator[GraphItem]:
        for member in self.members:
            if member.matches(**criteria):
                yield member

    def find_one(self, **criteria) -> Optional[GraphItem]:
        return next(self.find_all(**criteria), None)
