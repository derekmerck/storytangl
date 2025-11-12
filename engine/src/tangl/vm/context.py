# tangl/vm/context.py
"""
Execution context for one frame of resolution.
Thin wrapper around the graph, cursor, and scope providing deterministic RNG.
"""
from __future__ import annotations
from collections import ChainMap
from collections.abc import Mapping
from typing import TYPE_CHECKING, Iterable, Any
from uuid import UUID
import functools
from dataclasses import dataclass, field
from random import Random
import logging

from tangl.type_hints import Hash, StringMap
from tangl.utils.hashing import hashing_func
from tangl.core.graph import Graph, Node
from tangl.core.behavior import Behavior, BehaviorRegistry, CallReceipt, HandlerLayer
from .provision import (
    BuildReceipt,
    ProvisionOffer,
    Provisioner,
    ProvisioningPlan,
    ProvisioningResult,
)

if TYPE_CHECKING:
    from .traversal import TraversableSubgraph
    from .dispatch import Namespace as NS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# dataclass for simplified init and frozen, not serialized or tracked
@dataclass(frozen=True)
class Context:
    """
    Context(graph: Graph, cursor_id: UUID, step: int = -1)

    Immutable container of per‑frame execution state.

    Why
    ----
    Centralizes the data needed to resolve one step—graph, cursor, layered
    behavior registries, and a deterministic RNG. Handlers read from context;
    :class:`~tangl.vm.Frame` is responsible for sequencing phases and writing
    records.

    Key Features
    ------------
    * **Frozen** – safe to pass across phases; graph may be a watched proxy when event‑sourcing.
    * **Deterministic RNG** – :attr:`rand` is stable per ``(graph, cursor, step)``.
    * **Layered behaviors** – :attr:`cls_behaviors` caches ad-hoc handlers while
      :attr:`active_layers` inject application/system registries.
    * **Receipts** – :attr:`call_receipts` buffers per‑phase results for reducers.
    * **State hash** – :attr:`initial_state_hash` guards patch application.

    API
    ---
    - :attr:`graph` – working :class:`~tangl.core.Graph` (may be watched).
    - :attr:`cursor` – resolved :class:`~tangl.core.Node`.
    - :attr:`step` – integer step index used in journaling and RNG seed.
    - :attr:`cls_behaviors` – per-frame registry for inline handlers.
    - :attr:`active_layers` – iterable of :class:`~tangl.core.behavior.BehaviorRegistry`.
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
    call_receipts: list[CallReceipt] = field(default_factory=list)
    initial_state_hash: Hash = None

    # this is just a dataclass re-implementation of HasLocalBehaviors mixin
    # recall, anything with local behaviors is NOT serializable.
    # Mount for LOCAL behaviors on the context
    local_behaviors: BehaviorRegistry = field(default_factory=lambda: BehaviorRegistry(label="ctx.local.dispatch", handler_layer=HandlerLayer.LOCAL))
    # Could pass APPLICATION or override layers on creation
    active_layers: Iterable[BehaviorRegistry] = field(default_factory=list)

    def get_active_layers(self) -> Iterable[BehaviorRegistry]:
        layers = set()
        if self.active_layers:
            # We may have been initialized with a custom SYSTEM layer
            layers.update(self.active_layers)
        else:
            # Otherwise use vm_dispatch for SYSTEM
            from tangl.vm.dispatch import vm_dispatch
            layers.add(vm_dispatch)
        # And we always include any local behaviors.
        if self.local_behaviors:
            layers.add(self.local_behaviors)
        # Our graph may know what APPLICATION or AUTHOR domain it lives in
        if hasattr(self.graph, 'get_active_layers'):
            layers.update(self.graph.get_active_layers())
        # Or it may have its own LOCAL behaviors attached
        elif hasattr(self.graph, 'local_behaviors'):
            # attaching local behaviors to a caller is usually going to be _ad hoc_
            locs = self.graph.local_behaviors
            if locs:
                layers.add(locs)
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

    _ns_cache: dict[UUID, NS] = field(default_factory=dict)

    def get_ns(self, node: Node = None, nocache=False) -> NS:
        from tangl.vm.dispatch import do_get_ns
        node = node or self.cursor
        if nocache or node.uid not in self._ns_cache:
            logger.debug(f"getting fresh ns for {node!r}")

            # todo: this is super-hacky, but a quick patch for nested get_ns
            #       corrupting call receipts
            # stash current call receipts
            from copy import copy
            call_receipts = copy(self.call_receipts)

            raw_ns = do_get_ns(node, ctx=self)

            composed_maps: list[Mapping[str, Any]] = []
            graph_locals = getattr(self.graph, "locals", None)
            if isinstance(graph_locals, dict):
                composed_maps.append(graph_locals)
            elif graph_locals is not None:
                composed_maps.append(graph_locals)

            base_ns: dict[str, Any] = {
                "cursor": node,
                "graph": self.graph,
                "ctx": self,
            }
            composed_maps.append(base_ns)

            if isinstance(raw_ns, ChainMap):
                for existing in raw_ns.maps:
                    if any(existing is candidate for candidate in composed_maps):
                        continue
                    composed_maps.append(existing)
            else:  # pragma: no cover - defensive
                composed_maps.append(raw_ns)  # type: ignore[arg-type]

            self._ns_cache[node.uid] = ChainMap(*composed_maps)

            # restore
            self.call_receipts.clear()
            self.call_receipts.extend(call_receipts)

        return self._ns_cache[node.uid]

    provision_offers: dict[UUID | str, list[ProvisionOffer]] = field(default_factory=dict)
    provision_builds: list[BuildReceipt] = field(default_factory=list)
    journal_content: dict[str, dict] = field(default_factory=dict)
    planning_indexed_provisioners: list[tuple[int, Provisioner]] = field(default_factory=list)
    frontier_provision_results: dict[UUID, ProvisioningResult] = field(default_factory=dict)
    frontier_provision_plans: dict[UUID, ProvisioningPlan] = field(default_factory=dict)
