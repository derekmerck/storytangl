# tangl/vm38/runtime/ledger.py
"""Persistent session state for a single traversal.

The Ledger owns long-lived state that persists across player actions:
the graph, cursor position and history, return stack, and accumulated output.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Self
from uuid import UUID

from pydantic import Field, model_validator

from tangl.core import BehaviorRegistry, Entity, Graph, OrderedRegistry, Selector
from tangl.type_hints import UnstructuredData
from tangl.vm.traversable import TraversableEdge, TraversableNode

from .causality import CausalityMode
from .frame import Frame, PhaseCtx, StepTrace
from ..fragments import Fragment
from ..replay import (
    CausalityTransitionRecord,
    CheckpointRecord,
    RollbackRecord,
    StepRecord,
    get_replay_engine,
)
from ..replay.contracts import ReplayDelta

if TYPE_CHECKING:
    from tangl.vm import Dependency


__all__ = ["Ledger"]

logger = logging.getLogger(__name__)


class Ledger(Entity):
    """Persistent traversal state across player actions."""

    graph: Graph
    output_stream: OrderedRegistry = Field(default_factory=OrderedRegistry)
    local_behaviors: BehaviorRegistry = Field(
        default_factory=lambda: BehaviorRegistry(label="ledger.local.dispatch"),
        exclude=True,
    )

    cursor_id: UUID
    cursor_history: list[UUID] = Field(default_factory=list)

    replay_algorithm_id: str = "diff_v1"
    checkpoint_cadence: int = 1
    causality_mode: CausalityMode = CausalityMode.CLEAN
    causality_break_reason: str | None = None
    causality_break_step_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_stream_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "output_stream" not in data and "records" in data:
            payload = dict(data)
            payload["output_stream"] = payload["records"]
            return payload
        return data

    @property
    def records(self) -> OrderedRegistry:
        """Legacy alias for :attr:`output_stream`."""
        return self.output_stream

    @records.setter
    def records(self, value: OrderedRegistry) -> None:
        self.output_stream = value

    @property
    def cursor(self) -> TraversableNode:
        """The current node, resolved from the graph."""
        return self.graph.get(self.cursor_id)

    @cursor.setter
    def cursor(self, value: TraversableNode) -> None:
        if value is not None:
            self.cursor_id = value.uid

    @property
    def turn(self) -> int:
        """Distinct position changes, ignoring self-loops."""
        from tangl.vm.traversal import count_turns

        return count_turns(self.cursor_history)

    @property
    def step(self) -> int:
        """Alias for ``cursor_steps``."""
        return self.cursor_steps

    @step.setter
    def step(self, value: int) -> None:
        self.cursor_steps = value

    call_stack_ids: list[UUID] = Field(default_factory=list)
    last_redirect: dict | None = None
    redirect_trace: list[dict] = Field(default_factory=list)

    def _call_stack(self) -> list[TraversableEdge]:
        """Resolve call stack UIDs to edge objects (introspection only)."""
        call_stack: list[TraversableEdge] = []
        for edge_id in self.call_stack_ids:
            edge = self.graph.get(edge_id)
            if edge is None:
                raise ValueError(
                    f"Call stack contains unresolved edge id: {edge_id}"
                )
            call_stack.append(edge)
        return call_stack

    def push_call(self, edge: TraversableEdge) -> None:
        """Push a call edge onto the return stack."""
        if edge.return_phase is None:
            raise ValueError("Putting a call onto the stack requires a return phase/type")
        self.call_stack_ids.append(edge.uid)

    def pop_call(self) -> TraversableEdge:
        """Pop and return the most recent call edge."""
        call_edge_id = self.call_stack_ids.pop()
        return self.graph.get(call_edge_id)

    reentrant_steps: int = -1
    cursor_steps: int = -1
    choice_steps: int = -1

    user: Optional[Entity] = Field(None, exclude=True)
    user_id: Optional[UUID] = None

    @classmethod
    def from_graph(
        cls,
        graph: Graph,
        entry_id: UUID,
        *,
        uid: UUID | None = None,
    ) -> Self:
        """Construct and initialize a ledger at a graph entry node."""
        payload: dict[str, Any] = {"graph": graph, "cursor_id": entry_id}
        if uid is not None:
            payload["uid"] = uid
        ledger = cls(**payload)
        ledger._seed_counters(entry_id=entry_id)
        ledger.initialize_entry()
        return ledger

    def _seed_counters(self, entry_id: UUID | None = None) -> None:
        """Initialize cursor and counters without dispatch/pipeline execution."""
        entry_id = entry_id or self.cursor_id
        entry_node = self.graph.get(entry_id)
        if entry_node is None:
            raise ValueError(f"Entry node not found: {entry_id}")

        self.cursor_id = entry_node.uid
        self.cursor_history = [entry_node.uid]
        self.reentrant_steps = 0
        self.cursor_steps = 0
        self.choice_steps = 0
        self.call_stack_ids = []
        self.last_redirect = None
        self.redirect_trace = []
        self.causality_mode = CausalityMode.CLEAN
        self.causality_break_reason = None
        self.causality_break_step_id = None

    def initialize_entry(self) -> None:
        """Finalize entry initialization and persist initial checkpoint."""
        frame = self.get_frame()
        self.call_stack_ids = [e.uid for e in frame.return_stack]
        self.save_snapshot(force=True)

    def initialize_ledger(self, entry_id: UUID | None = None) -> None:
        """Backward-compatible initializer for entry setup."""
        self._seed_counters(entry_id=entry_id)
        self.initialize_entry()

    def model_post_init(self, __context) -> None:
        """Initialize fresh ledgers; preserve structured ledgers as provided."""
        if self.cursor_steps < 0:
            self._seed_counters()
        elif not self.cursor_history and self.cursor_id is not None:
            self.cursor_history.append(self.cursor_id)

    def get_frame(self) -> Frame:
        """Create an ephemeral frame for the next pipeline execution."""
        frame_meta: dict[str, Any] = {}
        if self.user is not None:
            frame_meta["user"] = self.user
        if self.user_id is not None:
            frame_meta["user_id"] = self.user_id
        frame_meta["causality_mode"] = self.causality_mode.value
        return Frame(
            self.graph,
            self.cursor,
            self.output_stream,
            self._call_stack(),
            local_behaviors=self.local_behaviors,
            step_base=self.cursor_steps,
            meta=frame_meta,
            causality_mode=self.causality_mode,
            mark_soft_dirty_callback=self.mark_soft_dirty,
            escalate_to_hard_dirty_callback=self.escalate_to_hard_dirty,
        )

    def _record_causality_transition(
        self,
        *,
        from_mode: CausalityMode,
        to_mode: CausalityMode,
        reason: str,
        step_id: str | None = None,
    ) -> None:
        step = max(self.cursor_steps, 0)
        self.output_stream.append(
            CausalityTransitionRecord(
                step=step,
                from_mode=from_mode.value,
                to_mode=to_mode.value,
                reason=reason,
                step_id=step_id,
                cursor_id=self.cursor_id,
            )
        )
        logger.warning(
            "Causality transition %s -> %s at step=%s cursor_id=%s reason=%s step_id=%s",
            from_mode.value,
            to_mode.value,
            step,
            self.cursor_id,
            reason,
            step_id,
        )

    def mark_soft_dirty(self, reason: str, step_id: str | None = None) -> bool:
        """Transition from CLEAN to SOFT_DIRTY and audit the change once."""
        if self.causality_mode is not CausalityMode.CLEAN:
            return False
        previous = self.causality_mode
        self.causality_mode = CausalityMode.SOFT_DIRTY
        self._record_causality_transition(
            from_mode=previous,
            to_mode=self.causality_mode,
            reason=reason,
            step_id=step_id,
        )
        return True

    def escalate_to_hard_dirty(self, reason: str, step_id: str | None = None) -> bool:
        """Escalate to HARD_DIRTY once; never downgrade within this session."""
        if self.causality_mode is CausalityMode.HARD_DIRTY:
            return False
        previous = self.causality_mode
        self.causality_mode = CausalityMode.HARD_DIRTY
        self.causality_break_reason = reason
        self.causality_break_step_id = step_id
        self._record_causality_transition(
            from_mode=previous,
            to_mode=self.causality_mode,
            reason=reason,
            step_id=step_id,
        )
        return True

    def _record_step(self, trace: StepTrace) -> None:
        """Build and append replay records for one traced frame hop."""
        engine = get_replay_engine(self.replay_algorithm_id)
        delta = engine.build_delta(before_graph=trace.before_graph, after_graph=trace.after_graph)
        delta_id: UUID | None = None

        if delta is not None:
            self.output_stream.append(delta)
            delta_id = delta.uid

        self.output_stream.append(
            StepRecord(
                step=trace.step,
                edge_id=trace.edge_id,
                cursor_id=trace.cursor_id,
                entry_phase=trace.entry_phase.name if trace.entry_phase is not None else None,
                was_choice=trace.was_choice,
                delta_id=delta_id,
                state_hash=trace.state_hash,
                call_stack_ids=list(trace.call_stack_ids),
                algorithm_id=self.replay_algorithm_id,
            )
        )

    @staticmethod
    def _selection_destination_dependency(edge: TraversableEdge) -> Optional["Dependency"]:
        from tangl.vm import Dependency

        graph = getattr(edge, "graph", None)
        if graph is None:
            return None

        deps = graph.find_edges(
            Selector(
                has_kind=Dependency,
                predecessor=edge,
                label="destination",
                satisfied=False,
            )
        )
        dep = next(deps, None)
        if dep is not None:
            return dep
        deps = graph.find_edges(
            Selector(has_kind=Dependency, predecessor=edge, satisfied=False)
        )
        return next(deps, None)

    def _provision_selected_destination(self, edge: TraversableEdge) -> None:
        if edge.successor is not None:
            return

        dep = self._selection_destination_dependency(edge)
        if dep is None:
            return

        from tangl.vm import Resolver

        ctx = PhaseCtx(
            graph=self.graph,
            cursor_id=self.cursor_id,
            step=max(self.cursor_steps, 0),
            causality_mode=self.causality_mode,
            mark_soft_dirty_callback=self.mark_soft_dirty,
            escalate_to_hard_dirty_callback=self.escalate_to_hard_dirty,
        )
        resolved = Resolver.from_ctx(ctx).resolve_dependency(
            dep,
            allow_stubs=self.causality_mode is CausalityMode.HARD_DIRTY,
            _ctx=ctx,
        )
        if resolved and dep.successor is not None and edge.successor is None:
            edge.set_successor(dep.successor, _ctx=ctx)

    def resolve_choice(self, edge_id: UUID, *, choice_payload: Any = None) -> None:
        """Resolve a player choice and sync frame results into ledger state."""
        edge = self.graph.get(edge_id)
        if edge is None:
            raise ValueError(f"Choice edge not found: {edge_id}")

        self._provision_selected_destination(edge)

        frame = self.get_frame()
        if hasattr(frame, "step_observer"):
            frame.step_observer = self._record_step
        frame.resolve_choice(edge, choice_payload=choice_payload)

        for call_edge in frame.return_stack:
            if call_edge is None:
                raise ValueError("Frame return stack contains a null edge")

        self.choice_steps += 1
        self.cursor_steps += frame.cursor_steps
        prev_id = self.cursor_history[-1] if self.cursor_history else None
        for node_id in frame.cursor_trace:
            if prev_id is not None and node_id == prev_id:
                self.reentrant_steps += 1
            prev_id = node_id
        self.cursor_id = frame.cursor.uid
        self.cursor_history.extend(frame.cursor_trace)
        self.call_stack_ids = [edge.uid for edge in frame.return_stack]
        self.last_redirect = frame.last_redirect
        self.redirect_trace = list(frame.redirect_trace)

        self.save_snapshot(cadence=self.checkpoint_cadence)

    @staticmethod
    def _coerce_fragment_record(record: Any) -> Fragment | None:
        """Normalize mixed fragment record shapes into vm38 fragments."""
        if isinstance(record, Fragment):
            return record
        fragment_type = getattr(record, "fragment_type", None)
        if fragment_type is None:
            return None
        step = int(getattr(record, "step", -1) or -1)
        payload: dict[str, Any] = {
            "fragment_type": str(fragment_type),
            "step": step,
        }
        for key in ("content", "text", "source_id", "edge_id", "available", "unavailable_reason"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return Fragment(**payload)

    def get_journal(self, *, since_step: int = 0, limit: int = 0) -> list[Fragment]:
        """Return output fragments in chronological order, optionally filtered."""
        fragments: list[Fragment] = []

        for record in self.output_stream.values():
            fragment = self._coerce_fragment_record(record)
            if fragment is None:
                continue
            if fragment.step >= since_step or fragment.step < 0:
                fragments.append(fragment)

        if limit > 0 and len(fragments) > limit:
            fragments = fragments[-limit:]

        return fragments

    def unstructure(self) -> UnstructuredData:
        """Serialize ledger state to plain data for persistence."""
        return {
            "uid": self.uid,
            "label": self.label,
            "cursor_id": self.cursor_id,
            "cursor_history": list(self.cursor_history),
            "cursor_steps": self.cursor_steps,
            "choice_steps": self.choice_steps,
            "reentrant_steps": self.reentrant_steps,
            "call_stack_ids": list(self.call_stack_ids),
            "last_redirect": self.last_redirect,
            "redirect_trace": self.redirect_trace,
            "causality_mode": self.causality_mode.value,
            "causality_break_reason": self.causality_break_reason,
            "causality_break_step_id": self.causality_break_step_id,
            "user_id": str(self.user_id) if self.user_id is not None else None,
            "replay_algorithm_id": self.replay_algorithm_id,
            "checkpoint_cadence": self.checkpoint_cadence,
            "graph": self.graph.unstructure(),
            "output_stream": self.output_stream.unstructure(),
        }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        """Reconstruct a ledger from serialized data."""
        def _coerce_uuid(value: UUID | str) -> UUID:
            if isinstance(value, UUID):
                return value
            return UUID(str(value))

        def _coerce_kind_refs(value: Any) -> Any:
            if isinstance(value, dict):
                normalized: dict[str, Any] = {}
                for key, item in value.items():
                    if key == "kind" and isinstance(item, str):
                        normalized[key] = Entity.dereference_cls_name(item) or item
                    else:
                        normalized[key] = _coerce_kind_refs(item)
                return normalized
            if isinstance(value, list):
                return [_coerce_kind_refs(item) for item in value]
            return value

        graph = Graph.structure(_coerce_kind_refs(data["graph"]))
        output_stream = OrderedRegistry.structure(_coerce_kind_refs(data.get("output_stream", {})))

        return cls(
            uid=_coerce_uuid(data["uid"]),
            label=data.get("label", ""),
            graph=graph,
            output_stream=output_stream,
            cursor_id=_coerce_uuid(data["cursor_id"]),
            cursor_history=[_coerce_uuid(uid) for uid in data.get("cursor_history", [])],
            cursor_steps=data.get("cursor_steps", -1),
            choice_steps=data.get("choice_steps", -1),
            reentrant_steps=data.get("reentrant_steps", -1),
            call_stack_ids=[_coerce_uuid(uid) for uid in data.get("call_stack_ids", [])],
            last_redirect=data.get("last_redirect"),
            redirect_trace=list(data.get("redirect_trace", [])),
            causality_mode=CausalityMode(data.get("causality_mode", CausalityMode.CLEAN.value)),
            causality_break_reason=data.get("causality_break_reason"),
            causality_break_step_id=data.get("causality_break_step_id"),
            user_id=_coerce_uuid(data["user_id"]) if data.get("user_id") else None,
            replay_algorithm_id=data.get("replay_algorithm_id", "diff_v1"),
            checkpoint_cadence=data.get("checkpoint_cadence", 1),
        )

    def save_snapshot(self, *, force: bool = False, cadence: int = 0) -> Optional[CheckpointRecord]:
        """Save a checkpoint if forced or cadence says one is due."""
        cadence = cadence if cadence > 0 else self.checkpoint_cadence
        should_save = force or (
            cadence > 0
            and self.choice_steps >= 0
            and (self.choice_steps % cadence) == 0
        )
        if not should_save:
            return None

        engine = get_replay_engine(self.replay_algorithm_id)
        checkpoint = engine.make_checkpoint(
            graph=self.graph,
            step=self.cursor_steps,
            cursor_id=self.cursor_id,
            call_stack_ids=self.call_stack_ids,
        )
        self.output_stream.append(checkpoint)
        return checkpoint

    def push_snapshot(self) -> Optional[CheckpointRecord]:
        """Legacy alias for forcing a checkpoint save."""
        return self.save_snapshot(force=True)

    def record_stack_snapshot(self) -> Optional[CheckpointRecord]:
        """Legacy compatibility alias for stack/snapshot persistence."""
        return self.save_snapshot(force=True)

    def _ordered_records(self) -> list[Entity]:
        # Preserve actual stream append order. HasOrder.seq is class-local and
        # cannot be used to globally sort mixed record kinds.
        return list(self.output_stream.values())

    def _step_records(self, *, upto_step: int | None = None) -> list[StepRecord]:
        selector = Selector(has_kind=StepRecord)
        records = [
            record for record in selector.filter(self.output_stream)
            if record.algorithm_id == self.replay_algorithm_id
        ]
        if upto_step is not None:
            records = [record for record in records if record.step <= upto_step]
        return sorted(records, key=lambda record: (record.step, record.seq))

    def _checkpoint_records(self) -> list[CheckpointRecord]:
        selector = Selector(has_kind=CheckpointRecord)
        records = [
            record for record in selector.filter(self.output_stream)
            if record.algorithm_id == self.replay_algorithm_id
        ]
        return sorted(records, key=lambda record: (record.step, record.seq))

    def rollback_to_step(self, target_step: int, *, reason: str | None = None) -> None:
        """Restore ledger state to ``target_step`` with destructive truncation."""
        if target_step < 0:
            raise ValueError("target_step must be >= 0")
        if target_step > self.cursor_steps:
            raise ValueError(
                f"target_step {target_step} must be <= current step {self.cursor_steps}"
            )
        if target_step == self.cursor_steps:
            return

        prior_step = self.cursor_steps
        engine = get_replay_engine(self.replay_algorithm_id)
        checkpoints = self._checkpoint_records()
        checkpoint = next(
            (record for record in reversed(checkpoints) if record.step <= target_step),
            None,
        )
        if checkpoint is None:
            raise RuntimeError("No checkpoint available for rollback")

        graph = engine.restore_checkpoint(checkpoint)
        all_active_steps = self._step_records(upto_step=target_step)
        replay_steps = [
            record for record in all_active_steps
            if checkpoint.step < record.step <= target_step
        ]

        for record in replay_steps:
            if record.delta_id is None:
                continue
            delta = self.output_stream.get(record.delta_id)
            if delta is None:
                raise RuntimeError(f"Missing delta for StepRecord {record.uid}")
            if not isinstance(delta, ReplayDelta):
                raise RuntimeError(f"Invalid delta type for StepRecord {record.uid}")
            graph = engine.apply_delta(graph=graph, delta=delta)

        final_cursor_id = checkpoint.cursor_id
        final_call_stack_ids = list(checkpoint.call_stack_ids)
        if all_active_steps:
            final_cursor_id = all_active_steps[-1].cursor_id
            final_call_stack_ids = list(all_active_steps[-1].call_stack_ids)

        history_start = self.cursor_history[0] if self.cursor_history else checkpoint.cursor_id
        if checkpoints and checkpoints[0].step == 0:
            history_start = checkpoints[0].cursor_id
        history: list[UUID] = [history_start]
        history.extend(record.cursor_id for record in all_active_steps)

        reentrant_steps = 0
        for index in range(1, len(history)):
            if history[index] == history[index - 1]:
                reentrant_steps += 1

        choice_steps = sum(1 for record in all_active_steps if record.was_choice)

        ordered_records = self._ordered_records()
        cutoff_index = -1
        for index, record in enumerate(ordered_records):
            record_step = getattr(record, "step", None)
            if isinstance(record_step, int) and record_step <= target_step:
                cutoff_index = index
        kept_records = ordered_records[: cutoff_index + 1] if cutoff_index >= 0 else []

        truncated_record_count = len(ordered_records) - len(kept_records)
        truncated_step_count = sum(1 for record in self._step_records() if record.step > target_step)

        new_stream = OrderedRegistry()
        new_stream.extend(kept_records)
        new_stream.append(
            RollbackRecord(
                resumed_step=target_step,
                prior_step=prior_step,
                truncated_record_count=truncated_record_count,
                truncated_step_count=truncated_step_count,
                reason=reason,
            )
        )

        self.output_stream = new_stream
        self.graph = graph
        self.cursor_id = final_cursor_id
        self.call_stack_ids = final_call_stack_ids
        self.cursor_steps = target_step
        self.choice_steps = choice_steps
        self.cursor_history = history
        self.reentrant_steps = reentrant_steps
        self.last_redirect = None
        self.redirect_trace = []
