from __future__ import annotations
from uuid import UUID
from datetime import datetime

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Graph, Edge, Node
from tangl.core.handlers import HandlerPriority
from .traversable import TraversableGraph, TraversableEdge, on_enter

class TraversalRecord(Entity):

    cursor_id: UUID
    enter_time: datetime = Field(default_factory=datetime.now)
    exit_edge_id: UUID = None
    exit_time: datetime = None
    state_update: dict = None
    _state_on_enter: dict = None

    def finalize(self, exit_edge: Edge):
        self.exit_time = datetime.now()
        self.exit_edge_id = exit_edge.uid
        # todo: compute the state/context update diff
        # if self._state_on_enter:
        #     new_state = exit_edge.story.unstructure()
        #     self.state_update = diff(new_state, self._state_on_enter)
        #     self._state_on_enter = None  # discard stashed state

class HasHistory(TraversableGraph):

    traversal_history: list[TraversalRecord] = Field(default_factory=list)

    def start_record(self, cursor_node: Node):
        new_record = TraversalRecord(cursor_id=cursor_node.uid)
        self.traversal_records.append(new_record)

    def finalize_record(self, exit_edge: Edge):
        self.traversal_records[-1].finalize(exit_edge=exit_edge)

    @on_enter.register(priority=HandlerPriority.EARLY, caller_cls=Graph)
    def _start_history_record(self, *, edge: TraversableEdge, **context):
        self.history.finalize_record(edge.predecessor)  # before anything is applied
        self.history.start_record(edge.successor)

    def rollback(self):
        ...
