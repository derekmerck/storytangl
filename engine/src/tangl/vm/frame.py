# tangl/vm/frame.py
from __future__ import annotations
from typing import Literal, Optional, Any, Callable, Type
import functools
from enum import IntEnum, Enum
from uuid import UUID
from dataclasses import dataclass, field
from copy import deepcopy
import logging
from random import Random

from tangl.type_hints import Step, StringMap as NS
from tangl.utils.hashing import hashing_func
from tangl.core.entity import Conditional
from tangl.core.registry import Registry
from tangl.core.graph import Graph, Edge, Node
from tangl.core.dispatch import JobReceipt
from tangl.core.domain import AffiliateDomain
from .context import Context
from .events import ReplayWatcher, Event, WatchedRegistry
from ..core import Entity

logger = logging.getLogger(__name__)


Fragment = Entity   # Trace content fragment
Patch = Entity      # Trace update/event fragment

class ResolutionPhase(IntEnum):

    INIT = 0         # Does not run, just indicates not started
    VALIDATE = 10    # check avail new cursor Predicate, return ALL true or None
    PLANNING = 20    # resolve Dependencies and Affordances; updates graph/data on frontier in place and GATHERS receipts
    PREREQS = 30     # return ANY (first) avail prereq edge to a provisioned node to break and redirect
    UPDATE = 40      # mutates graph/data in place and GATHERS receipts
    JOURNAL = 50     # return PIPES receipts to compose a list of FRAGMENTS
    FINALIZE = 60    # cleanup, commit events, consume resources, etc.; updates graph/data in place and PIPE receipts to compose a Patch
    POSTREQS = 70    # return ANY (first) avail postreq edge to avail, provisioned node to break and redirect

    def properties(self) -> tuple[Callable, Type]:
        """Aggregation func and expected final result type by phase"""
        _data = {
            self.INIT: None,
            self.VALIDATE: (JobReceipt.all_truthy,   bool),     # confirm all true
            self.PLANNING: (JobReceipt.gather,       Any),
            self.PREREQS:  (JobReceipt.first_result, Edge),     # check for any available jmp/jr
            self.UPDATE:   (JobReceipt.gather,       Any),
            self.JOURNAL:  (JobReceipt.last_result,  list[Fragment]), # pipe and compose a list of Fragments
            self.FINALIZE: (JobReceipt.last_result,  Patch),    # pipe and compose a Patch (if event sourced)
            self.POSTREQS: (JobReceipt.first_result, Edge)      # check for any available jmp/jr
        }
        return _data[self]

    # Otherwise we also need to guarantee that at least **one** selectable edge
    # to a provisioned node exists on the frontier.

    # todo: should store two patches per tick, pre-projection, post-projection, so projection
    #       can be reproduced on replay under different handlers for example?

P = ResolutionPhase

class ChoiceEdge(Edge, Conditional):
    # Need to introduce concept of selectable vs. automatically followed edges.
    # Previously called 'traversable edge', these ONLY link 'structural' nodes.
    trigger_phase: Optional[Literal[P.PREREQS, P.POSTREQS]] = None
    # If trigger phase is not None, edge will auto-trigger if conditions are met.
    # Otherwise, it is considered Selectable (overloaded term?) and will be presented
    # in the frame's session output.

# dataclass for simplified init, not serialized or tracked
@dataclass
class Frame:
    # Frame manages Context (graph, cursor) and the Phase bus
    # Context manages Scope (capabilities over active domain layers)
    # Scope is inferred from Graph, cursor node, latent domains
    graph: Graph
    cursor_id: UUID
    epoch: Step = -1
    domain_registries: list[Registry[AffiliateDomain]] = field(default_factory=list)

    event_sourced: bool = False  # track effects on a mutable copy
    event_watcher: ReplayWatcher = field(default_factory=ReplayWatcher)

    phase_receipts: dict[Enum, list[JobReceipt]] = field(default_factory=dict)
    phase_outcome:  dict[Enum, Any] = field(default_factory=dict)

    @property
    def cursor(self) -> Node:
        return self.graph.get(self.cursor_id)

    @property
    def domain_registry(self) -> Registry[AffiliateDomain]:
        # this is a convenience property that creates a registry
        # if self.registries is empty and returns the first.
        if not self.domain_registries:
            self.domain_registries = [Registry()]
        return self.domain_registries[0]

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
        return Context(graph, self.cursor_id, self.domain_registries)

    def _invalidate_context(self) -> None:
        if hasattr(self, "context"):
            del self.context

    @functools.cached_property
    def rand(self):
        # Guarantees the same RNG sequence given the same context for deterministic replay
        h = hashing_func(self.graph.uid, self.epoch, self.cursor.uid, digest_size=8)
        seed = int.from_bytes(h[:8], "big")
        return Random(seed)

    def get_ns(self, phase: ResolutionPhase) -> NS:
        base_ns = self.context.get_ns()
        # The frame itself also provides a ns domain layer
        frame_layer = {
            'cursor': self.cursor,
            'epoch': self.epoch,
            "phase": phase,         # phase annotation for handlers
            "rand": self.rand,
            "results": [],          # type: list[JobReceipt]
        }
        return base_ns.new_child(frame_layer)

    def run_phase(self, phase: P) -> Any:
        ns = self.get_ns(phase)  # creates context if necessary, resets results
        handlers = list(self.context.get_handlers(phase=phase))
        receipts = [h(ns) for h in handlers]

        # Did it iteratively in ns so a compositor would have access to previous results for pipe
        # for h in self.context.get_handlers(phase=phase):
        #     ns["results"].append(h(ns))  # add the receipt to the result stack

        agg_func, result_type = phase.properties()
        outcome = agg_func(*receipts)

        # stash results on the context for review/compositing
        self.phase_receipts[phase] = receipts
        self.phase_outcome[phase] = outcome

        return outcome

    def follow_edge(self, edge: Edge) -> Edge | None:
        logger.debug(f'Following edge {edge!r}')

        # This should be in the step, not in the control loop, I think
        self.epoch += 1
        self.cursor_id = edge.destination.uid
        # Use the destination, not edge.dest_id in case its an anonymous edge
        self._invalidate_context()       # updated the anchor, need to rebuild scope

        # Make sure that this cursor is allowed
        if not self.run_phase(P.VALIDATE):
            raise RuntimeError(f"Proposed next cursor is not valid!")

        # May mutate graph/data
        patch = self.run_phase(P.PLANNING)      # No-op for now

        # Check for prereq cursor redirects
        # todo: implement j/r redirect stack
        if nxt := self.run_phase(P.PREREQS):  # may set an edge to next cursor
            if isinstance(nxt, Edge):
                return nxt
            else:
                raise RuntimeError(f"Proposed prereq jump is not a valid edge {type(nxt)}!")

        patch = self.run_phase(P.UPDATE)         # No-op for now

        # todo: If we are using event sourcing, we _may_ need to recreate a preview graph now if context isn't holding a mutable copy and change events were logged

        # Generate the output content for the current state
        entry = self.run_phase(P.JOURNAL)
        # todo: compose and copy wherever to where-ever it goes, as entry nodes or into a separate journal object
        # todo: If fragments are stored as nodes, we should update the preview graph again since cleanup might want to see the journal.  Otherwise the journal needs to be stored somewhere else?  In the ns?

        # Cleanup bookkeeping
        patch = self.run_phase(P.FINALIZE)

        # check for postreq cursor redirects
        if nxt := self.run_phase(P.POSTREQS):   # may set an edge to next cursor
            if isinstance(nxt, Edge):
                return nxt
            else:
                raise RuntimeError(f"Proposed postreq jump is not a valid edge {type(nxt)}!")

        return None

    def resolve_choice(self, choice) -> None:
        # follows edges until no next edge is returned
        cur = choice
        while cur:
            cur = self.follow_edge(cur)
