from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Self, Literal
from uuid import UUID
from datetime import datetime

from pydantic import Field


if TYPE_CHECKING:
    from tangl.business.story.story_node import Story

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
        # todo: compute the state update diff
        # if self._state_on_enter:
        #     new_state = exit_edge.story.unstructure()
        #     self.state_update = diff(new_state, self._state_on_enter)


class TraversalHistory(Entity):
    traversal_records: list[TraversalRecord] = Field(default_factory=list)

    def record_entry(self, cursor_node: Node):
        new_record = TraversalRecord(cursor_id=cursor_node.uid)
        self.traversal_records.append(new_record)

    def record_exit(self, exit_edge: Edge):
        self.traversal_records[-1].finalize(exit_edge=exit_edge)

    def rollback(self, graph: TraversableGraph):
        ...

class HasTraversalHistory(HasContext):
    traversal_history: TraversalHistory

    on_follow_edge.register()
    def _record_cursor_update(self, edge: Edge, **context):
        self.traversal_history.record_entry(edge.cursor_node)






    def find_entry_point(self) -> Optional[TraversableEdge]:
        # Nodes with traversable children provide a context and need a default entry point
        entry_point = self.find_child(
            has_cls=TraversableNode,
            is_entry_point=True)  # type: TraversableNode

    @property
    def is_entry_point(self) -> bool:
        return "is_entry" in self.tags or \
               self.label in ["entry", "start"]



TraversableEdge = Edge[TraversableNode]

# from tangl.core.graph.handlers import Traversable, TraversableGraph,

    # def enter(self, **context):
    #     on_enter.execute(self, **context)
