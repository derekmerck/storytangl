from collections import defaultdict
from uuid import UUID
from typing import Optional
from dataclasses import dataclass, field

from ..registry import Registry
from .scope_mixin import ScopeMixin
from .domain import Domain
from .node import Node
from .edge import Edge, EdgeKind, EdgeTrigger

@dataclass(kw_only=True)
class Graph(ScopeMixin, Registry[Node]):

    edges_out: dict[UUID, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    edges_in: dict[UUID, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    def link(self,
             src: Node | UUID,
             dst: Node | UUID,
             kind: EdgeKind,
             *,
             directed: bool | None = None,
             trigger: EdgeTrigger | str | None = None,
             **_locals) -> Edge:
        src_uid = src if isinstance(src, UUID) else src.uid
        if src_uid not in self:
            raise RuntimeError(f"Tried to link, but source node {src_uid} not in graph")
        dst_uid = dst if isinstance(dst, UUID) else dst.uid
        if dst_uid not in self:
            raise RuntimeError(f"Tried to link, but destination node {dst_uid} not in graph")
        directed = directed if directed is not None else (kind is not EdgeKind.ASSOCIATION)
        if trigger and isinstance(trigger, str):
            trigger = EdgeTrigger[trigger.upper()]

        edge = Edge(src_uid=src_uid, dst_uid=dst_uid,
                    kind=kind, trigger=trigger, directed=directed, locals=_locals)
        self.edges_out[src_uid].append(edge)
        self.edges_in[dst_uid].append(edge)

        if not directed:  # ASSOCIATION → add mirror edge
            mirror = Edge(src_uid=dst_uid, dst_uid=src_uid,
                          kind=kind, directed=False)
            self.edges_out[dst_uid].append(mirror)
            self.edges_in[src_uid].append(mirror)
        return edge

    def unlink(self, edge: Edge) -> None:
        raise NotImplementedError()


