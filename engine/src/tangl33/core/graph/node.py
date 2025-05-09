from uuid import UUID
from typing import Any
from dataclasses import dataclass, field

from ..entity import Entity

@dataclass(kw_only=True)
class Node(Entity):
    parent_uid: UUID | None = None
    locals: dict[str, Any] = field(default_factory=dict)

    def iter_ancestors(self, *, graph):
        uid = self.parent_uid
        while uid:
            node = graph.get(uid)
            yield node
            uid = node.parent_uid
