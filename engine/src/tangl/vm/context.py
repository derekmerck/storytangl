# tangl/vm/context.py
"""
Execution context for one frame of resolution.
Thin wrapper around the graph, cursor, and scope providing deterministic RNG.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Iterable
from uuid import UUID
import functools
from dataclasses import dataclass, field
from random import Random
import logging

from tangl.type_hints import Hash, StringMap
from tangl.utils.hashing import hashing_func
from tangl.core.graph import Graph, Node
from tangl.core.behavior import Behavior, BehaviorRegistry, CallReceipt
from .provision import ProvisionOffer

if TYPE_CHECKING:
    from .traversal import TraversableSubgraph

logger = logging.getLogger(__name__)

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
    # domain_registries: list[AffiliateRegistry] = field(default_factory=list)
    call_receipts: list[CallReceipt] = field(default_factory=list)
    initial_state_hash: Hash = None

    local_behaviors: BehaviorRegistry = field(default_factory=BehaviorRegistry)
    # SYSTEM and APPLICATION layers
    active_layers: Iterable[BehaviorRegistry] = field(default_factory=list)

    def get_active_layers(self) -> Iterable[BehaviorRegistry]:
        from tangl.vm.dispatch import vm_dispatch
        # todo: get the graph's author layer as well
        layers = {vm_dispatch, *self.active_layers, self.local_behaviors}
        return layers

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

    # Composite phase helpers and storage
    # Composite phases invoke subphases and store intermediate results.
    # The gather-namespace subphase is so frequently used that it has
    # its own helper.

    _ns_cache: dict[UUID, StringMap] = field(default_factory=dict)

    def get_ns(self, node: Node = None, nocache=False) -> StringMap:
        from tangl.vm.dispatch import do_get_ns
        node = node or self.cursor
        if nocache or node.uid not in self._ns_cache:
            logger.debug(f"getting ns for {node!r}")
            self._ns_cache[node.uid] = do_get_ns(node, ctx=self)
        return self._ns_cache[node.uid]

    provision_offers: dict[UUID, ProvisionOffer] = field(default_factory=dict)
    journal_content: dict[str, dict] = field(default_factory=dict)
