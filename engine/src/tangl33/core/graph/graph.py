from collections import defaultdict
from uuid import UUID
from typing import Optional

from ..registry import Registry
from .node import Node
from .edge import Edge, EdgeKind, ChoiceTrigger


class Graph(Registry[Node]):

    edges_out: dict[UUID, list[Edge]] = defaultdict(list)
    edges_in: dict[UUID, list[Edge]] = defaultdict(list)

    def link(self,
             src: Node | UUID,
             dst: Node | UUID,
             kind: EdgeKind,
             *,
             directed: bool | None = None,
             trigger: ChoiceTrigger | str | None = None,
             **_locals) -> Edge:
        src_uid = src if isinstance(src, UUID) else src.uid
        dst_uid = dst if isinstance(dst, UUID) else dst.uid
        directed = directed if directed is not None else (kind is not EdgeKind.ASSOCIATION)
        if trigger and isinstance(trigger, str):
            trigger = ChoiceTrigger[trigger.upper()]

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
        ...

    domain: Optional['Domain'] = None
