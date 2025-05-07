from __future__ import annotations
from uuid import UUID
from typing import Callable, Optional

from pydantic import Field

from .requirement import Providable
from .entity import Entity
from .edge import Edge
from .registry import Registry
from .template import Template
from .step_hook import StepHook


class Node(Entity, Providable):

    children_ids: list[UUID] = Field(default_factory=list)

    redirects: list[tuple[Callable, Edge]] = Field(default_factory=list)
    continues: list[tuple[Callable, Edge]] = Field(default_factory=list)
    choices:   list[Edge] = Field(default_factory=list)

    content_tmpl: str | Callable | None = None

    # helper used by driver
    def _select(self, bucket, ctx):
        for pred, edge in bucket:
            if pred(ctx):
                return edge

class StructureNode(Node):
    # structure nodes, graphs, and domains can contribute step hooks
    step_hooks: list[StepHook] = Field(default_factory=list)


class Graph(Registry[Node]):

    domain: Domain = None
    cursor_id: UUID | None = None
    step_hooks: list[StepHook] = Field(default_factory=list)

    @property
    def cursor(self) -> Optional[Node]:
        if self.cursor_id:
            return self.registry[self.cursor_id]


class Domain(Entity, Providable):
    step_hooks: list[StepHook] = Field(default_factory=list)
    template_registry: Registry[Template] = Field(default_factory=Registry)
