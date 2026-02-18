"""Replay records emitted into the vm38 output stream."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.core38 import Graph, Record
from tangl.type_hints import UnstructuredData


class StepRecord(Record):
    """One replay step on the active traversal timeline."""

    step: int
    edge_id: UUID | None = None
    cursor_id: UUID
    entry_phase: str | None = None
    was_choice: bool = False
    delta_id: UUID | None = None
    state_hash: bytes = b""
    call_stack_ids: list[UUID] = Field(default_factory=list)
    algorithm_id: str = ""


class CheckpointRecord(Record):
    """Checkpoint record for fast rollback reconstruction."""

    step: int
    algorithm_id: str
    graph_payload: UnstructuredData
    state_hash: bytes
    cursor_id: UUID
    call_stack_ids: list[UUID] = Field(default_factory=list)

    def restore_graph(self) -> Graph:
        return Graph.structure(self.graph_payload)


class RollbackRecord(Record):
    """Monument record emitted after destructive rollback."""

    resumed_step: int
    prior_step: int
    truncated_record_count: int
    truncated_step_count: int
    reason: str | None = None

