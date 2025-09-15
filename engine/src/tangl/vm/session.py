# tangl/vm/session.py
from __future__ import annotations
from typing import Literal, Optional
import functools
from enum import IntEnum, Enum
from uuid import UUID
from dataclasses import dataclass, field
from copy import deepcopy
import logging

from tangl.type_hints import Step, StringMap as NS
from tangl.core.entity import Conditional
from tangl.core.graph import Graph, Edge, Node
from tangl.core.domain import DomainRegistry
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
    domain_registry: DomainRegistry = field(default_factory=DomainRegistry)

    event_sourced: bool = False  # track effects on a mutable copy
    event_watcher: ReplayWatcher = field(default_factory=ReplayWatcher)

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
        return Context(graph, self.cursor_id, self.epoch, self.domain_registry)

    def _invalidate_context(self) -> None:
        if hasattr(self, "context"):
            del self.context

    def get_ns(self, phase: ResolutionPhase) -> NS:
        base_ns = self.context.get_ns()
        # The session itself also provides a ns domain layer
        session_layer = {
            # cursor and epoch are included by the context layer
            "phase": phase,         # phase annotation for handlers
            "results": [],          # receipts from handlers run during this phase
        }
        return base_ns.new_child(session_layer)

    def run_phase(self, phase: P) -> NS:
        ns = self.get_ns(phase)          # creates context if necessary
        for h in self.context.get_handlers(phase=phase):
            ns["results"].append(h(ns))
        return ns

    def follow_edge(self, edge: Edge) -> Edge | None:
        logger.debug(f'Following edge {edge!r}')

        # This should be in the step, not in the control loop, I think
        self.epoch += 1
        self.cursor_id = edge.destination_id
        self._invalidate_context()       # updated the anchor, need to rebuild scope

        # Make sure that this cursor is allowed
        ns = self.run_phase(P.VALIDATE)
        res = ns["results"]
        if not all(res):
            raise RuntimeError(f"Proposed next cursor is not valid!")

        # May mutate graph/data
        ns = self.run_phase(P.PLANNING)      # No-op for now

        # Check for prereq cursor redirects
        # todo: implement j/r redirect stack
        ns = self.run_phase(P.PREREQS)  # may set an edge to next cursor
        res = ns["results"]
        if res and isinstance(res[-1], Edge):
            return res[-1]

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
        res = ns["results"]
        if res and isinstance(res[-1], Edge):
            return res[-1]
        return None

    def resolve_choice(self, choice) -> None:
        # follows edges until no next edge is returned
        cur = choice
        while cur:
            cur = self.follow_edge(cur)
