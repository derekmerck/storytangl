# tangl/vm/frame.py
"""
Frame drives the phase bus over one *resolution step* over a :class:`~tangl.core.graph.Graph`.
"""
from __future__ import annotations
from typing import Literal, Optional, Any, Callable, Type, Self, Iterable
import functools
from enum import IntEnum, Enum
from uuid import UUID
from dataclasses import dataclass, field
from copy import deepcopy, copy
import logging

from tangl.type_hints import Step
from tangl.core import StreamRegistry, Graph, Edge, Node, CallReceipt, BaseFragment, BehaviorRegistry
from tangl.core.behavior import HandlerLayer
from tangl.core.entity import Conditional
from .context import Context
from .provision import PlanningReceipt
from .replay import ReplayWatcher, WatchedRegistry, Patch
from .resolution_phase import ResolutionPhase as P

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ChoiceEdge(Edge, Conditional):
    """
    A selectable or auto-triggering control edge between structural nodes.

    - **trigger_phase**: If set to :data:`ResolutionPhase.PREREQS` or :data:`ResolutionPhase.POSTREQS`, the edge is auto-followed during that phase when its :class:`~tangl.core.entity.Conditional` predicate is satisfied.

    * Presents to the traversal orchestrator as a *choice* (no trigger) or jump automatically (with trigger).
    * Only links *structural* nodes; use domain handlers to mutate attached data.
    """
    trigger_phase: Optional[Literal[P.PREREQS, P.POSTREQS]] = None


@dataclass
class Frame:
    """
    Frame(graph: ~tangl.core.Graph, cursor_id: ~uuid.UUID)

    Drives one *resolution step* over a :class:`~tangl.core.graph.Graph`.

    Why
    ----
    Orchestrates the phase pipeline from the current cursor, collecting receipts,
    emitting journal fragments, and (optionally) producing a patch from watched
    mutations. Keeps the *business logic* in domain handlers; Frame just wires
    context and applies the aggregation contracts of :class:`ResolutionPhase`.

    Key Features
    ------------
    * **Context management** – builds :class:`~tangl.vm.context.Context` lazily,
      injecting layered behavior registries and invalidating them on moves.
    * **Phase execution** – :meth:`run_phase` discovers handlers via scope and
      reduces their :class:`~tangl.core.dispatch.call_receipt.CallReceipt` outputs.
    * **Event sourcing (optional)** – when ``event_sourced=True``, applies changes
      to a watched preview graph and emits a :class:`~tangl.vm.replay.patch.Patch`.
    * **Journal output** – pushes fragments/patches to :attr:`records` with step markers.

    API
    ---
    - :attr:`graph` – active graph being updated.
    - :attr:`cursor_id` – node id anchoring scope and traversal.
    - :attr:`records` – :class:`~tangl.core.record.StreamRegistry` receiving fragments/patches.
    - :meth:`run_phase(phase)<run_phase>` – execute a single phase; return aggregated outcome.
    - :meth:`follow_edge(edge)<follow_edge>` – advance the cursor and run the full phase pipeline once.
    - :meth:`resolve_choice(choice)<resolve_choice>` – keep following returned edges until no next edge.

    Notes
    -----
    The orchestrator should snapshot/commit via the ledger after resolution ends.
    """
    # Frame manages Context (graph, cursor) and the Phase bus
    # Context manages layered behavior registries for active domains
    graph: Graph
    cursor_id: UUID
    step: Step = 0

    local_behaviors: BehaviorRegistry = field(default_factory=lambda: BehaviorRegistry(label="frame.local.dispatch", handler_layer=HandlerLayer.LOCAL))
    # # SYSTEM, APPLICATION, AUTHOR layers
    # active_layers: Iterable[BehaviorRegistry] = field(default_factory=list)

    def get_active_layers(self) -> Iterable[BehaviorRegistry]:
        # We know that we are part of the SYSTEM layer
        from tangl.core.dispatch import core_dispatch
        from .dispatch import vm_dispatch
        layers = {vm_dispatch}
        # And we always include any local behaviors.
        if self.local_behaviors:
            layers.add(self.local_behaviors)
        return layers

    event_sourced: bool = False  # track effects on a mutable copy
    event_watcher: ReplayWatcher = field(default_factory=ReplayWatcher)

    phase_receipts: dict[Enum, list[CallReceipt]] = field(default_factory=dict)
    phase_outcome:  dict[Enum, Any] = field(default_factory=dict)

    # Practically, this is the output buffer for the step, so someone else needs
    # to be holding onto it when the frame goes out of scope if we want to access it.
    records: StreamRegistry = field(default_factory=StreamRegistry)

    @property
    def cursor(self) -> Node:
        return self.graph.get(self.cursor_id)

    def get_preview_graph(self):
        # create a disposable preview graph from the current event buffer
        _graph = deepcopy(self.graph)
        _graph = self.event_watcher.replay(_graph)
        return _graph

    @functools.cached_property
    def context(self) -> Context:
        if self.event_sourced:
            # Use a watched registry proxy if using event sourcing mechanism
            _graph = self.get_preview_graph()  # copy w events applied
            graph: Graph = WatchedRegistry(wrapped=_graph, watchers=[self.event_watcher])
        else:
            graph = self.graph
        logger.debug(f'Creating context with cursor id {self.cursor_id}')
        return Context(graph=graph,
                       cursor_id=self.cursor_id,
                       step=self.step,
                       active_layers=self.get_active_layers()
                       )

    def _invalidate_context(self) -> None:
        if hasattr(self, "context"):
            del self.context

    def run_phase(self, phase: P):
        from .dispatch import vm_dispatch

        receipts = vm_dispatch.dispatch(
            caller=self.cursor,
            ctx=self.context,
            task=phase,
        )
        # Iterate them out so we can reuse the variable
        receipts = list(receipts)

        agg_func, result_type = phase.properties()
        outcome = agg_func(*receipts)

        logger.debug(f'Ran {len(receipts)} handlers with final outcome {outcome} under {agg_func.__name__}')

        # stash results for review/compositing
        self.phase_receipts[phase] = receipts
        self.phase_outcome[phase] = outcome

        # Flush the call receipt buffer in context
        self.context.call_receipts.clear()

        return outcome

    def follow_edge(self, edge: Edge) -> Edge | None:
        logger.debug(f'Following edge {edge!r}')

        current_ctx = self.context
        if hasattr(edge, "apply_selected"):
            edge.apply_selected(ctx=current_ctx)  # type: ignore[call-arg]
        else:
            from tangl.vm.runtime import HasEffects  # local import to avoid circular deps

            if isinstance(edge, HasEffects):
                edge.apply_entry_effects(ctx=current_ctx)

        self.step += 1
        self.cursor_id = edge.destination.uid

        # Set a marker on the record stream
        self.records.set_marker(f"step-{self.step:04d}", "frame")

        # Use the destination, not edge.dest_id in case it is an anonymous edge
        self._invalidate_context()       # updated the anchor, need to rebuild scope

        # Make sure that this cursor is allowed
        if not self.run_phase(P.VALIDATE):
            logger.debug(f'receipt results: {[r.result for r in self.phase_receipts[P.VALIDATE]]}')
            logger.debug(f'receipt agg: {list(CallReceipt.gather_results(*self.phase_receipts[P.VALIDATE]))}')
            raise RuntimeError(f"Proposed next cursor is not valid!")

        baseline_state_hash = self.context.initial_state_hash

        # May mutate graph/data
        planning_receipt = self.run_phase(P.PLANNING)

        if isinstance(planning_receipt, PlanningReceipt):
            self.records.add_record(planning_receipt)

        # Check for prereq cursor redirects
        # todo: implement j/r redirect stack
        if nxt := self.run_phase(P.PREREQS):  # may set an edge to next cursor
            if isinstance(nxt, Edge):
                logger.debug(f'Found prereq edge {nxt!r}')
                return nxt
            else:
                raise RuntimeError(f"Proposed prereq jump is not a valid edge {type(nxt)}!")

        self.run_phase(P.UPDATE)         # No-op for now

        # todo: If we are using event sourcing, we _may_ need to recreate a preview graph now if context isn't holding a mutable copy and change events were logged

        # Generate the output content for the current state
        entry_fragments = self.run_phase(P.JOURNAL)

        # Cleanup bookkeeping
        finalize_receipt = self.run_phase(P.FINALIZE)

        if isinstance(finalize_receipt, PlanningReceipt):
            self.records.add_record(finalize_receipt)

        if entry_fragments:
            self.records.push_records(
                *entry_fragments,
                marker_type="journal",
                marker_name=f"step-{self.step:04d}"
            )

        patch: Patch | None = None
        if self.event_sourced and self.event_watcher.events:
            patch_events = list(self.event_watcher.events)
            patch = Patch(
                events=patch_events,
                registry_id=self.graph.uid,
                registry_state_hash=baseline_state_hash,
            )
            self.records.add_record(patch)
            # Apply the patch to the authoritative graph so subsequent phases
            # observe the committed state. Skip state hash validation during the
            # apply step because finalize may have already updated metadata
            # (e.g., requirement bindings) prior to event emission.
            patch_for_apply = patch.model_copy(update={"registry_state_hash": None})
            self.graph = patch_for_apply.apply(self.graph)
            # ready for next frame
            self.event_watcher.clear()
            # Invalidate the cached context so POSTREQS rebuilds against the
            # updated graph state.
            self._invalidate_context()

        if patch is not None:
            self.phase_outcome[P.FINALIZE] = patch

        # check for postreq cursor redirects
        if nxt := self.run_phase(P.POSTREQS):   # may set an edge to next cursor
            if isinstance(nxt, Edge):
                logger.debug(f'Found postreq edge {nxt!r}')
                return nxt
            else:
                raise RuntimeError(f"Proposed postreq jump is not a valid edge {type(nxt)}!")

        return None

        # todo: should store two patches per tick, pre-projection, post-projection,
        #       so projection can be reproduced on replay under different handlers,
        #       for example?

    def jump_to_node(self, destination: Node | UUID, *, include_postreq: bool = False) -> None:
        """Teleport to ``destination`` by following an anonymous edge."""

        if isinstance(destination, UUID):
            node = self.graph.get(destination)
        else:
            node = destination

        if node is None:
            raise RuntimeError(f"Destination {destination!r} not found in graph")

        from tangl.core.graph.edge import AnonymousEdge

        bootstrap_edge = AnonymousEdge(destination=node)
        next_edge = self.follow_edge(bootstrap_edge)

        while isinstance(next_edge, ChoiceEdge):
            trigger_phase = getattr(next_edge, "trigger_phase", None)

            if trigger_phase == P.PREREQS:
                next_edge = self.follow_edge(next_edge)
                continue

            if trigger_phase == P.POSTREQS and include_postreq:
                next_edge = self.follow_edge(next_edge)
                continue

            break

    def resolve_choice(self, choice: ChoiceEdge) -> None:
        """
        Follow a user's choice and continue through any automatic redirects.

        Executes the phase pipeline for ``choice``, then keeps following
        any edges returned by PREREQ/POSTREQ redirect handlers. Stops when
        a stable cursor is reached (no more auto-triggered edges).

        **Important**: Only edges with ``trigger_phase`` set are auto-followed,
        and only if they pass their predicate guard given the current namespace.
        Single blocking choices still require explicit user selection - use
        this method after the user picks from available choices.

        Notes
        -----
        Orchestrator should call :meth:`Ledger.push_snapshot` after resolution
        completes to persist the new state.

        See Also
        --------
        get_available_choices : List choices for user selection
        ChoiceEdge.trigger_phase : Mark edges for automatic following
        """

        cur = choice
        while cur:
            cur = self.follow_edge(cur)
