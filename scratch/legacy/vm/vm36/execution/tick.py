from dataclasses import dataclass, field
from uuid import UUID, uuid4
from typing import Optional, Mapping
import hashlib, random
from collections import ChainMap, defaultdict
import logging

from tangl.core36 import Graph, Facts, Node, EdgeKind
from tangl.vm36.scoping import Scope
from .patch import Effect, Op, Patch, apply_patch, canonicalize, resolve_fqn

logger = logging.getLogger(__name__)

def blake_seed(*parts: bytes) -> int:
    # Guarantees the same RNG sequence given the same context for deterministic replay
    h = hashlib.blake2b(digest_size=8)
    for p in parts: h.update(p)
    return int.from_bytes(h.digest(), "big")


# --- todo: suggested update code ------

@dataclass
class CursorState:
    uid: Optional[UUID] = None
    label: Optional[str] = None

from .effects import EffectBuffer

@dataclass
class StepContext:
    # instance vars
    story_id: UUID
    epoch: int
    choice_id: str
    base_hash: int
    graph: Graph = None  # read-only base snapshot
    cursor: CursorState = field(default_factory=CursorState)

    # working vars
    facts: Facts = None  # working var
    buf: EffectBuffer = field(default_factory=EffectBuffer)
    scope: Optional[Scope] = None
    rng: random.Random = None
    io: list[dict] = field(default_factory=list)

    # for domain aware scope assembly
    domains: object | None = None
    globals_ns: Mapping[str, object] | None = None
    # next cursor handoffs
    next_cursor_uid: Optional[UUID] = None

    def __post_init__(self):
        # Deterministic RNG using blake-based seed
        self._seed = blake_seed(
            self.story_id.bytes,
            self.epoch.to_bytes(8, "big"),
            self.choice_id.encode(),
            self.base_hash.to_bytes(8, "big", signed=True),
        )
        self.rng = random.Random(self._seed)
        if self.scope is None:
            self.refresh_scope()

        self._attach_effect_shims()

    # deterministic allocation
    def allocate_uid(self) -> UUID:
        hi = self.rng.getrandbits(64)
        lo = self.rng.getrandbits(64)
        return UUID(int=(hi << 64) | lo)

    # graph cloning strategy for preview
    def _clone_graph(self, base: Graph) -> Graph:
        try:
            from .patch import resolve_fqn
            return Graph.from_dto(base.to_dto(), resolve_fqn)  # type: ignore[attr-defined]
        except Exception:
            try:
                return Graph(**base.model_dump())  # type: ignore[attr-defined]
            except Exception:
                return base.clone()  # type: ignore[attr-defined]

    # Effect Buffer Shims
    def preview(self) -> Graph:
        return self.buf.preview(self.graph, clone_fn=self._clone_graph)

    def _attach_effect_shims(self):
        self.journal = self.buf.journal
        self.effects = self.buf.effects

    def _prov(self, default):
        return getattr(self, "_handler", default)

    def create_node(self, cls_fqn: str, **data) -> UUID:
        return self.buf.create_node(self.allocate_uid, cls_fqn,
                                    provenance=self._prov(("effects", "create_node")),
                                    **data)

    def add_edge(self, src: UUID, dst: UUID, kind: str) -> UUID:
        return self.buf.add_edge(self.allocate_uid, src, dst, kind,
                                 provenance=self._prov(("effects", "add_edge")))

    def del_edge(self, eid: UUID) -> None:
        self.buf.del_edge(eid, provenance=self._prov(("effects", "del_edge")))

    def set_attr(self, uid: UUID, path: tuple[str, ...], value) -> None:
        self.buf.set_attr(uid, path, value, provenance=self._prov(("effects", "set_attr")))

    def say(self, frag: dict) -> None:
        self.buf.say(frag)

    def to_patch(self, tick_id: UUID) -> Patch:
        return self.buf.to_patch(tick_id, rng_seed=self._seed, io=self.io)

    def update_facts(self, g: Graph) -> None:
        self.facts = Facts.compute(g)

    # ------- Scope -------

    def _attach_legacy_shims(self, scope):
        # Provide a by-phase overlay on the context
        self.scope_handlers_by_phase = scope.handlers_by_phase
        self.scope_handlers = scope.handlers
        self.active_domains = scope.active_domains
        self.ns = scope.ns

    def refresh_scope(self) -> None:
        """Build a fresh Scope from the current PREVIEW (read-your-writes) and set it on ctx."""
        g2 = self.preview()
        self.update_facts(g2)

        # Prefer the pre-commit handoff cursor if present
        anchor_uid = self.next_cursor_uid or self.cursor.uid

        if anchor_uid is None:
            first = next(iter(g2.nodes()), None)
            if isinstance(first, Node):
                anchor_uid = first.uid
                self.cursor.uid = anchor_uid
                self.cursor.label = first.label
        # If still no anchor (empty graph), skip assembling scope for now
        if anchor_uid is None:
            logger.debug(f"No cursor uid found for {self}")
            return
        self.scope = Scope.assemble(g2, self.facts, cursor_uid=anchor_uid)

        # --- legacy shims PhaseBus may look for -----------------------------
        # self._attach_legacy_shims(self.scope)

    # manually created scope attachment
    def mount_scope(self, scope: Scope) -> None:
        self.scope = scope
        self._attach_legacy_shims(self.scope)

    # -------- utilities -------

    # Expose an “effective cursor” utility (some helpers call this)
    # todo: seems redundant?
    # def effective_cursor(self) -> Optional[UUID]:
    #     return self.cursor.uid

    # Used by exec handlers to request a post-commit cursor handoff
    def set_next_cursor(self, node_or_uid) -> None:
        uid = getattr(node_or_uid, "uid", None) or node_or_uid
        self.next_cursor_uid = uid
