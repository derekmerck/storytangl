from uuid import UUID
from typing import Any
from dataclasses import dataclass, field

from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class Node(ScopeMixin, Entity):
    parent_uid: UUID | None = None

    def iter_ancestors(self, *, graph):
        uid = self.parent_uid
        while uid:
            node = graph.get(uid)
            yield node
            uid = node.parent_uid
