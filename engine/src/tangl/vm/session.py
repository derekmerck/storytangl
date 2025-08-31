# tangl/vm/session.py
import functools
from typing import Any, TypeVar, TYPE_CHECKING
from enum import Enum
from uuid import UUID
from dataclasses import dataclass, field
from copy import deepcopy
import logging

if TYPE_CHECKING:
    from collections import ChainMap

from tangl.type_hints import StringMap, Step
from tangl.core.graph import Graph, Edge, Node
from tangl.core.domain import DomainRegistry, NS
from .context import Context
from .events import ReplayWatcher, Event, WatchedRegistry

logger = logging.getLogger(__name__)


class ResolutionPhase(Enum):
    INIT = "init"            # Does not run, just indicates not ready
    VALIDATE = "validate"
    PROVISION = "provision"
    UPDATE = "update"
    JOURNAL = "journal"
    CLEANUP = "cleanup"

P = ResolutionPhase

# dataclass for simplified init, not serialized or tracked
@dataclass
class Session:
    # Session manages Context (graph, cursor)
    # Context manages Scope (capabilities over active domain layers)
    # Scope is inferred from Graph, cursor node, latent domains
    graph: Graph
    cursor_id: UUID
    step: Step = -1
    domain_registry: DomainRegistry = field(default_factory=DomainRegistry)

    event_sourced: bool = False  # track effects on a mutable copy
    event_watcher: ReplayWatcher = field(default_factory=ReplayWatcher)

    @property
    def cursor(self) -> Node:
        return self.graph.get(self.cursor_id)

    def get_preview_graph(self):
        # create a disposable preview graph from the current event buffer
        _graph = deepcopy(self.graph)
        _graph = Event.replay_all(self.event_watcher.events, _graph)
        return _graph

    @functools.cached_property
    def context(self) -> Context:
        if self.event_sourced:
            _graph = self.get_preview_graph()  # copy w events applied
            graph: Graph = WatchedRegistry(wrapped=_graph, watchers=[self.event_watcher])
        else:
            graph = self.graph
        logger.debug(f'Creating context with cursor id {self.cursor_id}')
        return Context(graph, self.cursor_id, self.step, self.domain_registry)

    def _invalidate_context(self) -> None:
        if hasattr(self, "context"):
            del self.context

    def get_ns(self, phase: ResolutionPhase) -> NS:
        ns = self.context.get_ns()
        # The session itself also provides a ns domain layer
        # could just write these directly into the context layer or move the context
        # layer vars here, but we will separate for consistency for now
        session_layer = {'results': [], 'phase': phase}
        return ns.new_child(session_layer)

    def run_phase(self, phase: P) -> NS:
        ns = self.get_ns(phase)          # creates context if necessary
        for h in self.context.get_handlers(phase=phase):
            ns["results"].append(h(ns))
        return ns

    def follow_edge(self, edge: Edge) -> Edge | None:
        logger.debug(f'Following edge {edge!r}')
        self.step += 1
        self.cursor_id = edge.destination_id
        self._invalidate_context()
        _ = self.run_phase(P.VALIDATE)  # may set an edge to next cursor

        # terminate trampoline explicitly for now
        return None

        # res = ns["results"]
        # if res and isinstance(res[-1], Edge):
        #     return res[-1]
        # # self.run_phase(P.PROVISION)
        # self.run_phase(P.UPDATE)
        # # If we are using event sourcing, we _may_ need to recreate a preview graph now, depending on whether the context holds a mutable copy or the immutable source
        # # self.run_phase(P.JOURNAL)
        # # todo: and copy contents wherever they go, nodes or a separate journal object
        # ns = self.run_phase(P.CLEANUP)  # may set an edge to next cursor
        # res = ns["results"]
        # if res and isinstance(res[-1], Edge):
        #     return res[-1]
        # return None

    def resolve_choice(self, choice) -> None:
        # follows edges until no next edge is returned
        cur = choice
        while cur:
            cur = self.follow_edge(cur)
