from uuid import UUID
from typing import Any
from dataclasses import field

from ..entity import Entity

class Node(Entity):
    parent_uid: UUID | None = None
    locals: dict[str, Any] = field(default_factory=dict)
    def iter_ancestors(self, graph): ...