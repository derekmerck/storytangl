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
from contextlib import contextmanager

from tangl.type_hints import Hash, StringMap
from tangl.utils.hashing import hashing_func
from tangl.core.graph import Graph, Node, Subgraph
from tangl.core.behavior import Behavior, BehaviorRegistry, CallReceipt, HandlerLayer
from tangl.ir.core_ir.base_script_model import BaseScriptItem
from .provision import (
    BuildReceipt,
    ProvisionOffer,
    Provisioner,
    ProvisioningPlan,
    ProvisioningResult,
)

if TYPE_CHECKING:
    from tangl.core.record.base_fragment import BaseFragment

    from .traversal import TraversableSubgraph
    from .dispatch import Namespace as NS

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# todo: bunch of story-related stuff embedded in here.  add an 'enrichment'
#       layer to the ns or something, but don't be referencing concepts and
#       locations.

# todo: enrichments should be computed like ns, once per existing object
#       and cached, using the ns of whoever requested/injected the
#       enrichment I think.

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

    # Journal pipeline state
    concept_descriptions: dict[str, str] | None = field(default=None)
    current_content: str | list[BaseFragment] | None = field(default=None)
    current_choices: list[BaseFragment] | None = field(default=None)

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

    @property
    def current_location(self) -> "Location | None":
        """Return the :class:`~tangl.story.concepts.location.Location` attached to the cursor."""

        cursor = self.cursor
        if not hasattr(cursor, "get_concepts"):
            return None

        from tangl.story.concepts.location.location import Location

        for concept in cursor.get_concepts():
            if isinstance(concept, Location):
                return concept
        return None

    @contextmanager
    def _fresh_call_receipts(self):
        from copy import copy
        _call_receipts = copy(self.call_receipts)
        self.call_receipts.clear()
        yield self
        self.call_receipts.clear()
        self.call_receipts.extend(_call_receipts)

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


            with self._fresh_call_receipts():
                # stash current call receipts so they aren't affected by the subdispatch

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
                # self.call_receipts.clear()
                # self.call_receipts.extend(call_receipts)

        return self._ns_cache[node.uid]

    def set_concept_descriptions(self, mapping: dict[str, str]) -> None:
        """Store concept descriptions for template rendering."""

        object.__setattr__(self, "concept_descriptions", mapping)


    def set_current_content(self, content: str | list[BaseFragment] | None) -> None:
        """Store current content during journal pipeline."""

        object.__setattr__(self, "current_content", content)

    def set_current_choices(self, choices: list[BaseFragment] | None) -> None:
        """Store current choices during journal pipeline."""

        object.__setattr__(self, "current_choices", choices)

    provision_offers: dict[UUID | str, list[ProvisionOffer]] = field(default_factory=dict)
    provision_builds: list[BuildReceipt] = field(default_factory=list)
    journal_content: dict[str, dict] = field(default_factory=dict)
    planning_indexed_provisioners: list[tuple[int, Provisioner]] = field(default_factory=list)
    frontier_provision_results: dict[UUID, ProvisioningResult] = field(default_factory=dict)
    frontier_provision_plans: dict[UUID, ProvisioningPlan] = field(default_factory=dict)


class MaterializationContext(Context):
    """Context flowing through the materialization dispatch pipeline."""

    template: BaseScriptItem
    payload: dict
    parent_container: Subgraph | None
    node: Node | None

    def __init__(
        self,
        *,
        template: BaseScriptItem,
        graph: Graph,
        payload: dict,
        parent_container: Subgraph | None = None,
        node: Node | None = None,
        cursor_id: UUID | None = None,
        step: int = 0,
    ) -> None:
        super().__init__(graph=graph, cursor_id=cursor_id or graph.uid, step=step)
        object.__setattr__(self, "template", template)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "parent_container", parent_container)
        object.__setattr__(self, "node", node)

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: D401 - short override
        """Allow mutation of materialization state within dispatch."""

        if name in {"node", "payload", "parent_container", "template"}:
            object.__setattr__(self, name, value)
            return

        super().__setattr__(name, value)
