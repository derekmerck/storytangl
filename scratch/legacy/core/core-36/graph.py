# tangl/core/graph.py
"""
# tangl.core.graph

Author-facing **surface graph** with explicit adjacency and **silent mutators** for replay.

**Design choices**

- `Graph.items` is a small `Registry[GraphItem]` (UID → object).
- `out_idx` / `in_idx` hold **edge UID sets** for fast local traversals without scanning `items`.
- All public mutations go through **Effects** (see `tangl.core.types` and `vm.patch.apply_patch`).
  This class exposes `_add_*_silent` / `_del_*_silent` for **replay only**.

**Why silent mutators?**
During patch replay we must not emit new Effects or validations, or we’d loop forever.
Silent mutators apply changes to the surface model *exactly as recorded* in the patch.

**Downstream dependencies**
- `vm.patch.apply_patch` calls `_add_*_silent`/`_del_*_silent`.
- `vm.scopes.assemble_namespace` uses `contains` edges via `Facts` to build the ancestor chain.
- `StepContext.move_under()` leans on `find_edge_ids(..., kind="contains")` to reparent by Effects.
"""
from __future__ import annotations
from typing import Iterator, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from .entity import Node, Edge, GraphItem
from .registry import Registry

class Graph(BaseModel):
    """Surface graph: authors see this; VM applies patches via silent mutators."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: Registry[GraphItem] = Field(default_factory=Registry[GraphItem])
    out_idx: dict[UUID, set[UUID]] = Field(default_factory=dict, description="node uid -> set(edge uid)")
    in_idx:  dict[UUID, set[UUID]] = Field(default_factory=dict, description="node uid -> set(edge uid)")

    # ---- queries ----
    def get(self, uid: UUID) -> Optional[GraphItem]: return self.items.get(uid)

    def __len__(self) -> int:
        return len(self.items)

    def nodes(self) -> Iterator[Node]:
        yield from self.items.find(has_cls=Node)

    def edges(self) -> Iterator[Edge]:
        yield from self.items.find(has_cls=Edge)

    def find_edges(self, node: Node, *, direction: Literal["in", "out", "both"] = "both", **criteria) -> Iterator[Edge]:
        """
        Iterate edges incident to `node`, filtered by `criteria` (exact attribute matches).

        **Why this API?** Most engine/domain code wants to stay on **objects** while navigating;
        this uses adjacency to avoid a full scan and then dereferences edge objects for you.
        """
        u = node.uid
        if direction in ("out", "both"):
            for eid in self.out_idx.get(u, ()):
                e = self.items.get(eid)
                if isinstance(e, Edge) and e.matches(**criteria):
                    yield e
        if direction in ("in", "both"):
            for eid in self.in_idx.get(u, ()):
                e = self.items.get(eid)
                if isinstance(e, Edge) and e.matches(**criteria):
                    yield e

    def find_edge_ids(
            self,
            *,
            src: Optional[UUID] = None,
            dst: Optional[UUID] = None,
            kind: Optional[str] = None,
    ) -> set[UUID]:
        """
        Return **edge UIDs** filtered by `(src, dst, kind)`.

        **Why a UID-level variant?**
        - Effect builders sometimes need **IDs** (e.g., to emit `DEL_EDGE(eid)`), and scanning objects
          just to get back to IDs is noisy.
        - Uses adjacency first, then optional kind check, so it’s still O(degree) for typical calls.

        See also: `find_edges(...)` for the object-level traversal.
        """
        # todo: I still think we might merge this with find_edges to be more DRY
        # candidate sets from adjacency
        cand: set[UUID] | None = None
        if src is not None:
            cand = set(self.out_idx.get(src, set()))
        if dst is not None:
            ids = set(self.in_idx.get(dst, set()))
            cand = ids if cand is None else (cand & ids)
        if cand is None:
            # no src/dst given: start from all edges
            cand = {e.uid for e in self.edges()}

        if kind is None:
            return cand

        # filter by kind
        out: set[UUID] = set()
        for eid in cand:
            e = self.items.get(eid)
            if isinstance(e, Edge) and e.kind == kind:
                out.add(eid)
        return out

    # ---- silent mutators ----
    # used only by patch replay; never emit events or validations.
    def _add_node_silent(self, node: Node) -> None:
        """
        Replay helper: add a node **without** validation, events, or index updates beyond `items`.

        Called exclusively by `vm.patch.apply_patch`. Never call from author code;
        use Effects via `StepContext.create_node(...)` instead.
        """
        self.items.add(node)

    def _del_node_silent(self, uid: UUID) -> None:
        """
        Replay helper: delete a node and **all incident edges** from both `items` and adjacency.

        **Why delete incident edges here?** Patches are canonicalized with deletes first,
        but an explicit safety net avoids dangling adjacency in hand-written migrations/tests.
        """
        # remove incident edges from adjacency
        for eid in list(self.out_idx.get(uid, ())):
            self._del_edge_id_silent(eid)
        for eid in list(self.in_idx.get(uid, ())):
            self._del_edge_id_silent(eid)
        self.items.remove(uid)
        self.out_idx.pop(uid, None); self.in_idx.pop(uid, None)

    def _add_edge_silent(self, edge: Edge) -> None:
        """
        Replay helper: add an edge and update adjacency, **without** emitting new Effects.

        Invariants upheld:
        - `edge.uid` is unique (enforced by the Effect generator),
        - adjacency sets are updated atomically.
        """
        self.items.add(edge)
        self.out_idx.setdefault(edge.src_id, set()).add(edge.uid)
        self.in_idx.setdefault(edge.dst_id, set()).add(edge.uid)

    def _del_edge_id_silent(self, eid: UUID) -> None:
        e = self.items.get(eid)
        if isinstance(e, Edge):
            self.out_idx.get(e.src_id, set()).discard(eid)
            self.in_idx.get(e.dst_id, set()).discard(eid)
            self.items.remove(eid)

    # ---- DTO snapshot ----
    def to_dto(self) -> dict:
        """
        Snapshot to a portable DTO:

        - Items as a nested DTO list (FQN + data) via `Registry.to_dto()`.
        - Adjacency as `str(UUID) → [str(UUID)]` to keep encoders simple.

        Downstream: storage layer encodes this DTO (pickle/orjson/…).
        """
        # todo: would it be more DRY to rebuild adjacency index rather than saving it?
        return {
            "items": self.items.to_dto(),
            "out_idx": {str(k): [str(e) for e in v] for k, v in self.out_idx.items()},
            "in_idx":  {str(k): [str(e) for e in v] for k, v in self.in_idx.items()},
        }

    @classmethod
    def from_dto(cls, dto: dict, resolver) -> "Graph":
        """
        Rehydrate a graph from a DTO (`to_dto` inverse). `resolver` maps FQN → class.

        **Why not pickle?** We want **runtime portability** and schema control.
        FQNs let you ship the same IR to other interpreters/runtimes.
        """
        items = Registry[GraphItem].from_dto(dto["items"], resolver)
        def unstr(d):
            return {UUID(k): {UUID(e) for e in vs} for k, vs in d.items()}
        return cls(items=items, out_idx=unstr(dto.get("out_idx", {})), in_idx=unstr(dto.get("in_idx", {})))