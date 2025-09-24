# tangl/vm/session.py
from __future__ import annotations
from typing import Literal, Optional, Any
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

logger = logging.getLogger(__name__)

# In principle, could merge validate/prereqs, cleanup/postreqs, but they have
# different aggregation mechanisms, so it's maybe best to keep them distinct.

class ResolutionPhase(IntEnum):

    INIT = 0         # Does not run, just indicates not started
    VALIDATE = 10    # check avail new cursor Predicate, return ALL true or None
    PLANNING = 20    # resolve Dependencies and Affordances; updates graph/data on frontier in place and GATHERS receipts
    PREREQS = 30     # return ANY (first) avail prereq edge to a provisioned node to break and redirect
    UPDATE = 40      # mutates graph/data in place and GATHERS receipts
    JOURNAL = 50     # return PIPE of generated fragments, needs post-processor composite and commit; previously "RENDER"
    FINALIZE = 60    # cleanup, commit events, consume resources, etc.; updates graph/data in place and GATHERS receipts
    POSTREQS = 70    # return ANY (first) avail postreq edge to avail, provisioned node to break and redirect

    # Otherwise we also need to guarantee that at least **one** selectable edge
    # to a provisioned node exists on the frontier.

P = ResolutionPhase

class ChoiceEdge(Edge, Conditional):
    # Need to introduce concept of selectable vs. automatically followed edges.
    # Previously called 'traversable edge', these ONLY link 'structural' nodes.
    trigger_phase: Optional[Literal[P.PREREQS, P.POSTREQS]] = None
    # If trigger phase is not None, edge will auto-trigger if conditions are met.
    # Otherwise, it is considered Selectable and will be presented in the session
    # output.

# dataclass for simplified init, not serialized or tracked
@dataclass
class Session:
    # Session manages Context (graph, cursor)
    # Context manages Scope (capabilities over active domain layers)
    # Scope is inferred from Graph, cursor node, latent domains
    graph: Graph
    cursor_id: UUID
    epoch: Step = -1
    domain_registries: list[Registry[AffiliateDomain]] = field(default_factory=list)

    event_sourced: bool = False  # track effects on a mutable copy
    event_watcher: ReplayWatcher = field(default_factory=ReplayWatcher)

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
        # The session itself also provides a ns domain layer
        session_layer = {
            'cursor': self.cursor,
            'epoch': self.epoch,
            "phase": phase,         # phase annotation for handlers
            "rand": self.rand,
            "results": [],          # type: list[JobReceipt]
        }
        return base_ns.new_child(session_layer)

    def run_phase(self, phase: P) -> NS:
        ns = self.get_ns(phase)          # creates context if necessary, resets results
        for h in self.context.get_handlers(phase=phase):
            ns["results"].append(h(ns))  # add the receipt to the result stack
        return ns

    def follow_edge(self, edge: Edge) -> Edge | None:
        logger.debug(f'Following edge {edge!r}')

        # This should be in the step, not in the control loop, I think
        self.epoch += 1
        self.cursor_id = edge.destination.uid
        # Use the destination, not edge.dest_id in case its an anonymous edge
        self._invalidate_context()       # updated the anchor, need to rebuild scope

        # Make sure that this cursor is allowed
        ns = self.run_phase(P.VALIDATE)
        if not JobReceipt.all_true(*ns.get('results')):
            raise RuntimeError(f"Proposed next cursor is not valid!")

        # May mutate graph/data
        ns = self.run_phase(P.PLANNING)      # No-op for now

        # Check for prereq cursor redirects
        # todo: implement j/r redirect stack
        ns = self.run_phase(P.PREREQS)  # may set an edge to next cursor
        nxt = JobReceipt.last_result(*ns.get('results'))
        if isinstance(nxt, Edge):
            return nxt

        ns = self.run_phase(P.UPDATE)         # No-op for now

        # todo: If we are using event sourcing, we _may_ need to recreate a preview graph now if context isn't holding a mutable copy and change events were logged

        # Generate the output content for the current state
        ns = self.run_phase(P.JOURNAL)
        # todo: compose and copy wherever to where-ever it goes, as entry nodes or into a separate journal object
        # todo: If fragments are stored as nodes, we should update the preview graph again since cleanup might want to see the journal.  Otherwise the journal needs to be stored somewhere else?  In the ns?

        # Cleanup bookkeeping
        ns = self.run_phase(P.FINALIZE)

        # check for postreq cursor redirects
        ns = self.run_phase(P.POSTREQS)    # may set an edge to next cursor
        nxt = JobReceipt.last_result(*ns.get('results'))
        if isinstance(nxt, Edge):
            return nxt
        return None

    def resolve_choice(self, choice) -> None:
        # follows edges until no next edge is returned
        cur = choice
        while cur:
            cur = self.follow_edge(cur)
