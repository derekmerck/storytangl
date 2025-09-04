# tangl/core/graph/subgraph.py
from __future__ import annotations
from typing import Optional, Iterator, TYPE_CHECKING
from uuid import UUID
from enum import Enum

from pydantic import Field

from .graph import GraphItem, Graph

if TYPE_CHECKING:
    from .node import Node

# todo: should be a registry b/c its a collection?
class Subgraph(GraphItem):
    subgraph_type: Optional[Enum] = None  # No need to enumerate this yet
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
        item._invalidate_parent_attr()
        self.member_ids.append(item.uid)

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
        return next(self.find_one(**criteria), None)
