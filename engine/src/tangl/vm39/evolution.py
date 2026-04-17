from __future__ import annotations
from uuid import UUID
from enum import auto, IntEnum
from typing import Optional, Iterator

from pydantic import Field

from tangl.core39 import Entity, Record, OrderedRegistry, Graph, Node, Edge, Subgraph, BehaviorRegistry, ExecContext, Priority, EntityDelta


##############################
# LEDGER
##############################

class CursorUpdateRecord(Record):
    new_cursor_id: UUID
    registry_delta: EntityDelta

class StepRecord(Record):
    step_num: int
    cursor_update_ids: list[UUID] = Field(default_factory=list)

class EvolutionaryLedger(Entity):
    graph: Graph
    cursor_history: list[UUID] = Field(default_factory=list)  # every node a cursor passes through on update
    step_history: list[int] = Field(default_factory=list)    # nodes where the cursor stops
    journal: OrderedRegistry = Field(default_factory=OrderedRegistry)

    @property
    def cursor(self) -> Optional[TraversableNode]:
        if len(self.cursor_history) > 0:
            cursor_id = self.cursor_history[-1]
            return self.graph.get(cursor_id)
        return None

    @cursor.setter
    def cursor(self, value: TraversableNode):
        self.cursor_history.append(value.uid)

    def num_steps(self) -> int:
        return len(self.step_history)

    def num_cursor_updates(self) -> int:
        return len(self.cursor_history)

    def restore_state_to(self, step: int):
        last_snapshot = self.journal.find_one(kind=Graph, range=[0, step], sort_key=lambda x: -x.sort_key)
        deltas = self.journal.find_all(kind=EntityDelta, range=[last_snapshot, step])
        graph = last_snapshot.materialize()
        for delta in deltas:
            delta.apply(graph)
        self.graph = graph

    def get_step_ctx(self):
        return StepContext(
            graph = self.graph.evolve(),
            authorities = [self.behaviors],
            journal = self.journal,
        )

    def resolve_step(self, edge: TraversableEdge) -> None:
        # a single step may involve many individual cursor updates
        step_ctx = self.get_step_ctx()
        while edge is not None:
            edge = step_ctx.follow_edge(edge)

        self.cursor_history.extend(step_ctx.cursor_entries)
        self.journal.extend(step_ctx.journal_entries)
        self.step_history.append(len(self.cursor_history))


class UpdatePhase(IntEnum):
    VALIDATE = 10
    PLANNING = 20
    PREREQS = 30
    UPDATE = 40
    JOURNAL = 50
    FINALIZE = 60
    POSTREQS = 70


class StepContext(ExecContext):

    graph: Graph
    cursor: TraversableNode
    authorities: list[BehaviorRegistry] = Field(default_factory=list)

    # @on_task("step_graph", priority=UpdatePhase.VALIDATE)
    # def extend_frontier(self):
    #     for edge in self.graph.edges_from(kind=TraversableEdge,
    #                                       predecessor=self.cursor,
    #                                       satisfied=False):
    #         GraphPlanner.resolve_node(edge.successor)

    def follow_edge(self, edge: TraversableEdge) -> Optional[TraversableEdge]:
        ...


class TraversableNode(Node):
    ...

class TraversableEdge(Edge):

    @property
    def predecessor(self) -> TraversableNode:
        return super().predecessor

    @property
    def successor(self) -> TraversableNode:
        return super().successor

class TraversableNeighborhood(Subgraph[TraversableNode]):

    def enter(self, via: TraversableEdge) -> TraversableNode:
        ...

    def exit(self, via: TraversableEdge) -> TraversableNode:
        ...

