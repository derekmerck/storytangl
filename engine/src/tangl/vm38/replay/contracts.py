"""Replay engine contracts for vm38.

These protocols keep :class:`~tangl.vm38.runtime.ledger.Ledger` algorithm-agnostic.
Diff-based replay is one implementation; future event-sourced variants should
implement the same contracts.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tangl.core38 import Graph

from .records import CheckpointRecord


@runtime_checkable
class ReplayDelta(Protocol):
    """A replayable state delta."""

    def apply_to(self, graph: Graph) -> Graph:
        """Apply this delta to ``graph`` and return the resulting graph."""


@runtime_checkable
class ReplayEngine(Protocol):
    """Algorithm interface for replay and rollback."""

    def algorithm_id(self) -> str:
        """Stable algorithm identifier used on replay records."""

    def build_delta(self, *, before_graph: Graph, after_graph: Graph) -> ReplayDelta | None:
        """Build a delta between two graph states, or ``None`` when unchanged."""

    def apply_delta(self, *, graph: Graph, delta: ReplayDelta) -> Graph:
        """Apply a delta to ``graph``."""

    def make_checkpoint(
        self,
        *,
        graph: Graph,
        step: int,
        cursor_id,
        call_stack_ids,
    ) -> CheckpointRecord:
        """Create a checkpoint record for the current graph state."""

    def restore_checkpoint(self, checkpoint: CheckpointRecord) -> Graph:
        """Restore and verify graph state from a checkpoint."""

