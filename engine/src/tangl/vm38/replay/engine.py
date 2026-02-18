"""Replay engine implementations for vm38."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from tangl.core38 import Graph

from .contracts import ReplayDelta, ReplayEngine
from .patch import Event, OpEnum, Patch
from .records import CheckpointRecord


DEFAULT_ALGORITHM_ID = "diff_v1"


class DiffReplayEngine:
    """Diff-based replay engine.

    Deltas are represented as :class:`Patch` records containing create/update/delete
    events for graph members.
    """

    def algorithm_id(self) -> str:
        return DEFAULT_ALGORITHM_ID

    def build_delta(self, *, before_graph: Graph, after_graph: Graph) -> Patch | None:
        events: list[Event] = []

        before_ids = set(before_graph.members.keys())
        after_ids = set(after_graph.members.keys())

        for item_id in sorted(before_ids - after_ids, key=str):
            events.append(
                Event(
                    operation=OpEnum.DELETE,
                    item_id=item_id,
                )
            )

        for item_id in sorted(after_ids - before_ids, key=str):
            item = after_graph.get(item_id)
            if item is None:
                continue
            events.append(
                Event(
                    operation=OpEnum.CREATE,
                    item_id=item_id,
                    value=item.unstructure(),
                )
            )

        for item_id in sorted(before_ids & after_ids, key=str):
            before_item = before_graph.get(item_id)
            after_item = after_graph.get(item_id)
            if before_item is None or after_item is None:
                continue
            if before_item.value_hash() == after_item.value_hash():
                continue
            events.append(
                Event(
                    operation=OpEnum.UPDATE,
                    item_id=item_id,
                    value=after_item.unstructure(),
                )
            )

        if not events:
            return None

        return Patch(
            registry_id=after_graph.uid,
            initial_registry_value_hash=before_graph.value_hash(),
            final_registry_value_hash=after_graph.value_hash(),
            events=events,
        )

    def apply_delta(self, *, graph: Graph, delta: ReplayDelta) -> Graph:
        return delta.apply_to(graph)

    def make_checkpoint(
        self,
        *,
        graph: Graph,
        step: int,
        cursor_id: UUID,
        call_stack_ids: Iterable[UUID],
    ) -> CheckpointRecord:
        return CheckpointRecord(
            step=step,
            algorithm_id=self.algorithm_id(),
            graph_payload=graph.unstructure(),
            state_hash=graph.value_hash(),
            cursor_id=cursor_id,
            call_stack_ids=list(call_stack_ids),
        )

    def restore_checkpoint(self, checkpoint: CheckpointRecord) -> Graph:
        graph = checkpoint.restore_graph()
        if graph.value_hash() != checkpoint.state_hash:
            raise ValueError("Checkpoint hash mismatch")
        return graph


def get_replay_engine(algorithm_id: str) -> ReplayEngine:
    """Resolve a replay engine by id."""
    if algorithm_id == DEFAULT_ALGORITHM_ID:
        return DiffReplayEngine()
    raise ValueError(f"Unknown replay algorithm: {algorithm_id}")
