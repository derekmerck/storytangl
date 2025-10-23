# tangl/vm/context.py
"""
Execution context for one frame of resolution.
Thin wrapper around the graph, cursor, and scope providing deterministic RNG.
"""
from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
from uuid import UUID
import functools
from dataclasses import dataclass, field
from random import Random
from collections import ChainMap

from tangl.type_hints import Hash
from tangl.utils.hashing import hashing_func
from tangl.core.graph import Graph, Node
from tangl.core.domain import Scope, NS, AffiliateRegistry
from tangl.core.dispatch import Behavior, CallReceipt
from .vm_dispatch.on_get_ns import on_get_ns

if TYPE_CHECKING:
    from .domain import TraversableDomain


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
    * **Receipts** – :attr:`call_receipts` buffers per‑phase results for reducers.
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
    - :attr:`call_receipts` – LIFO stack of :class:`~tangl.core.CallReceipt`.

    Notes
    -----
    Context does not define persistence or commit behavior; the ledger/orchestrator
    handles snapshot/patch writes after resolution.
    """
    graph: Graph
    cursor_id: UUID
    step: int = -1
    domain_registries: list[AffiliateRegistry] = field(default_factory=list)
    call_receipts: list[CallReceipt] = field(default_factory=list)
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
        lines.append("Handlers for ns:")
        names = [h.func.__name__ for h in self.scope.get_handlers(job="namespace")]
        lines.append(f"  ns: {', '.join(names)}")
        return "\n".join(lines)

    @staticmethod
    def _get_ns(scope: Scope) -> NS:
        maps = []
        for d in scope.active_domains:
            # todo: how do we include other registry layers?
            #       we always do global/app/author and don't worry about d's ancestors?
            #       this is bootstrapping, so we have to accept some constraints...
            domain_maps = on_get_ns.dispatch(caller=d, ctx=None)
            maps.extend(CallReceipt.gather_results(*domain_maps))
        return ChainMap(*maps)

    def get_ns(self) -> NS:
        """Bootstrap ctx by calling get_vars on every domain in active
        domains and creating."""
        return self._get_ns(self.scope)

    def get_handlers(self, **criteria) -> Iterator[Behavior]:
        # can pass phase in filter criteria if useful
        return self.scope.get_handlers(**criteria)

    def get_traversable_domain_for_node(self, node: Node) -> TraversableDomain | None:
        """Return the :class:`TraversableDomain` that contains ``node`` if available."""

        from tangl.vm.domain import TraversableDomain  # Local import to avoid cycle

        for domain in self.scope.active_domains:
            if isinstance(domain, TraversableDomain) and node.uid in domain.member_ids:
                return domain
        return None
