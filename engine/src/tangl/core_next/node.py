from uuid import UUID
from typing import Callable, Optional

from pydantic import Field

from .base import Entity, Identifiable, Providable
from .registry import Registry

class Edge(Identifiable):
    predecessor_id: UUID | None = None
    successor_id: UUID
    return_after: bool = False   # jump‑return

class Node(Entity, Providable):
    children_ids: list[UUID] = Field(default_factory=list)
    redirects: list[tuple[Callable, Edge]] = []
    continues: list[tuple[Callable, Edge]] = []
    choices:   list[Edge] = []
    content_tmpl: str | Callable | None = None

    # helper used by driver
    def _select(self, bucket, ctx):
        for pred, edge in bucket:
            if pred(ctx):
                return edge

class Graph(Registry[Node]):
    cursor_id: UUID | None = None

    @property
    def cursor(self) -> Optional[Node]:
        if self.cursor_id:
            return self.registry[self.cursor_id]
