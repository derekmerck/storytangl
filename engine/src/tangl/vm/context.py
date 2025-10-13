# tangl/vm/context.py
"""
Execution context for one frame of resolution.
Thin wrapper around the graph, cursor, and scope providing deterministic RNG.
"""
from __future__ import annotations
from typing import Iterator, Any
from uuid import UUID
import functools
from dataclasses import dataclass, field
from random import Random

from tangl.type_hints import Hash
from tangl.core.graph import Graph, Node
from tangl.core.domain import Scope, NS, AffiliateRegistry
from tangl.core.dispatch import Handler, JobReceipt
from tangl.utils.hashing import hashing_func


# dataclass for simplified init and frozen, not serialized or tracked
@dataclass(frozen=True)
class Context:
    """
    Context(graph: Graph, cursor_id: UUID, step: int = -1)

    Immutable container of per‑frame execution state.

    Why
    ----
    Centralizes the data needed to resolve one step—graph, cursor, registries,
    and a deterministic RNG—while caching the derived :class:`~tangl.core.Scope`.
    Handlers read from context; :class:`~tangl.vm.Frame` is responsible for
    sequencing phases and writing records.

    Key Features
    ------------
    * **Frozen** – safe to pass across phases; graph may be a watched proxy when event‑sourcing.
    * **Deterministic RNG** – :attr:`rand` is stable per ``(graph, cursor, step)``.
    * **Cached scope** – computed once from :attr:`graph`, :attr:`cursor_id`, and
      :attr:`domain_registries`.
    * **Receipts** – :attr:`job_receipts` buffers per‑phase results for reducers.
    * **State hash** – :attr:`initial_state_hash` guards patch application.

    API
    ---
    - :attr:`graph` – working :class:`~tangl.core.Graph` (may be watched).
    - :attr:`cursor` – resolved :class:`~tangl.core.Node`.
    - :attr:`step` – integer step index used in journaling and RNG seed.
    - :attr:`domain_registries` – registries of :class:`~tangl.core.domain.AffiliateDomain`.
    - :attr:`scope` – cached :class:`~tangl.core.Scope`.
    - :attr:`rand` – :class:`random.Random` seeded for replay.
    - :meth:`get_ns` – return merged namespace.
    - :meth:`get_handlers` – iterate handlers matching criteria (e.g., ``phase=…``).
    - :attr:`job_receipts` – LIFO stack of :class:`~tangl.core.JobReceipt`.

    Notes
    -----
    Context does not define persistence or commit behavior; the ledger/orchestrator
    handles snapshot/patch writes after resolution.
    """
    graph: Graph
    cursor_id: UUID
    step: int = -1
    domain_registries: list[AffiliateRegistry] = field(default_factory=list)
    job_receipts: list[JobReceipt] = field(default_factory=list)
    initial_state_hash: Hash = None

    def __post_init__(self):
        # Set initial hash on frozen object
        object.__setattr__(self, "initial_state_hash", hashing_func(self.graph._state_hash()))

    @functools.cached_property
    def rand(self):
        # Guarantees the same RNG sequence given the same graph.uid, cursor.uid, and step for deterministic replay
        h = hashing_func(self.graph.uid, self.cursor.uid, self.step, digest_size=8)
        seed = int.from_bytes(h[:8], "big")
        return Random(seed)

    @property
    def cursor(self) -> Node:
        if self.cursor_id not in self.graph:
            raise RuntimeError(f"Bad cursor id in context {self.cursor_id} not in {[k for k in self.graph.keys()]}")
        return self.graph.get(self.cursor_id)

    @functools.cached_property
    def scope(self) -> Scope:
        # Since Context is frozen wrt the scope parts, we never need to invalidate this.
        return Scope(graph=self.graph,
                     anchor_id=self.cursor_id,
                     domain_registries=self.domain_registries)

    def inspect_scope(self) -> str:
        lines = []
        lines.append(f"Available domains:")
        for dr in self.domain_registries:
            for d in dr.values():
                lines.append(f" - {d.__class__.__name__}:{d.get_label()}")
        lines.append("Active domains:")
        for d in self.scope.active_domains:
            lines.append(f" - {d.__class__.__name__}:{d.get_label()}")
        lines.append("Handlers by phase:")
        from .frame import ResolutionPhase as P
        for ph in P:
            names = [h.func.__name__ for h in self.scope.get_handlers(phase=ph)]
            lines.append(f"  {ph.name}: {', '.join(names)}")
        return "\n".join(lines)

    def get_ns(self) -> NS:
        return self.scope.namespace

    def get_handlers(self, **criteria) -> Iterator[Handler]:
        # can pass phase in filter criteria if useful
        return self.scope.get_handlers(**criteria)

    def get_traversable_domain_for_node(self, node: Node) -> "TraversableDomain" | None:
        """Return the :class:`TraversableDomain` that contains ``node`` if available."""

        from tangl.vm.domain import TraversableDomain  # Local import to avoid cycle

        for domain in self.scope.active_domains:
            if isinstance(domain, TraversableDomain) and node.uid in domain.member_ids:
                return domain
        return None
