# tangl/vm/session.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from uuid import UUID, uuid4
import zlib

from tangl.core36.graph import Graph
from tangl.persist.repo import Repository
from tangl.persist.ser import Serializer, PickleSerializer
from tangl.projection.journal import DiscourseIndex
from tangl.vm36.execution.patch import Patch
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from .tick import StepContext
from .patch import apply_patch


def graph_hash(g: Graph) -> int:
    # simple stable hash of DTO bytes (pickle for now, later orjson)
    import pickle
    dto = g.to_dto()
    return zlib.adler32(pickle.dumps(dto))  # 32-bit is fine for seeding

@dataclass
class GraphSession:
    graph_id: UUID
    repo: Repository
    serializer: Serializer = field(default_factory=PickleSerializer)
    snapshot_every: int = 100
    version: int = 0
    graph: Graph = field(default_factory=Graph)

    cursor_uid: UUID | None = None             # NEW
    domains: DomainRegistry | None = None      # NEW
    discourse: DiscourseIndex = field(default_factory=DiscourseIndex)  # NEW read-side

    def load_or_init(self, resolver: Callable[[str], type]) -> None:
        snap = self.repo.load_latest_snapshot(self.graph_id)
        if snap:
            self.version, blob = snap
            dto = self.serializer.loads(blob)
            self.graph = Graph.from_dto(dto, resolver)
        else:
            self.version, self.graph = 0, Graph()

    def set_cursor(self, uid: UUID) -> None:
        if self.graph.get(uid) is None:
            raise ValueError(f"cursor {uid} not in graph")
        self.cursor_uid = uid

    def run_tick(self, choice_id: str, build: Callable[[StepContext], None]) -> Patch:
        ctx = StepContext(
            story_id=self.graph_id,
            epoch=self.version,
            choice_id=choice_id,
            base_hash=graph_hash(self.graph),
            graph=self.graph,
            domains=self.domains
        )

        # # Optional: mount initial scope (base graph) if cursor+domains present
        # if self.cursor_uid is not None and self.domains is not None:
        #     facts = ctx.facts
        #     scope = Scope.assemble(self.graph, facts, self.cursor_uid, domains=self.domains)
        #     node = self.graph.get(self.cursor_uid)
        #     label = getattr(node, "label", None) if node else None
        #     ctx.mount_scope(scope)

        # Client/build code will typically:
        #   - bus.run(VALIDATE, ctx)
        #   - bus.run(EXECUTE, ctx)
        #   - refresh_scope_for_phase(ctx, self.domains)    # uses preview
        #   - bus.run(JOURNAL, ctx)
        build(ctx)

        patch = ctx.to_patch(tick_id=uuid4())

        # persist & apply
        patch_blob = self.serializer.dumps(patch)
        new_version = self.repo.append_patch(self.graph_id, self.version, patch_blob, idem_key=None)
        apply_patch(self.graph, patch)

        # update discourse read-side
        self.discourse.add_patch(patch)

        # snapshot occasionally
        if new_version % self.snapshot_every == 0:
            snap_blob = self.serializer.dumps(self.graph.to_dto())
            self.repo.save_snapshot(self.graph_id, new_version, snap_blob)

        self.version = new_version

        # Advance the real cursor after commit, if a handoff happened
        if ctx.next_cursor_uid is not None:
            self.cursor_uid = ctx.next_cursor_uid

        return patch
