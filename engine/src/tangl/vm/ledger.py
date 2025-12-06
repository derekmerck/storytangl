# tangl/vm/ledger.py
"""
State holder for the live graph, cursor, and record stream (snapshots, patches, journal).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, Iterable
import logging
from pydantic import Field
from uuid import UUID

from tangl.type_hints import UnstructuredData
from tangl.core import Entity, Graph, StreamRegistry, Snapshot, BehaviorRegistry
from .frame import Frame, StackFrame
from .stack_snapshot import StackSnapshot

if TYPE_CHECKING:
    from tangl.service.user.user import User
    from .replay import Patch
else:
    User = Entity

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Ledger(Entity):
    """
    Ledger(graph: Graph, cursor_id: ~uuid.UUID, records: StreamRegistry, domains: list[~tangl.core.Domain])

    Owns the working graph and the append-only record stream.

    Why
    ----
    Centralizes state for a running narrative: the active :class:`~tangl.core.Graph`,
    the current cursor, and the :class:`~tangl.core.StreamRegistry` of
    immutable :class:`~tangl.core.Record` artifacts. Provides helpers to
    snapshot, recover, and spin up :class:`~tangl.vm.Frame` executions.

    Key Features
    ------------
    * **Snapshots** – :meth:`push_snapshot` materializes a :class:`~tangl.core.Snapshot` of the graph.
    * **Recovery** – :meth:`recover_graph_from_stream` restores state by replaying patches after the last snapshot.
    * **Journal access** – :meth:`get_journal` returns fragment sections by marker.
    * **Frame factory** – :meth:`get_frame` constructs a frame bound to this ledger.
    * **Cadence** – :attr:`snapshot_cadence` hints how often to snapshot.

    API
    ---
    - :attr:`graph` – current graph state.
    - :attr:`cursor_id` – node id used by new frames.
    - :attr:`records` – append-only stream (snapshots, patches, fragments).
    - :attr:`step` – external step counter (not mutated by frames).
    - :attr:`domains` – optional meta domains active at the ledger level.
    - :attr:`snapshot_cadence` – default snapshot interval.
    - :meth:`push_snapshot` – append a graph snapshot to the stream.
    - :meth:`maybe_push_snapshot` – conditional snapshot helper.
    - :meth:`recover_graph_from_stream` – restore a graph from snapshot+patches.
    - :meth:`get_journal` – iterate fragments in a named section.
    - :meth:`get_frame` – create a :class:`~tangl.vm.Frame` bound to this ledger.

    Notes
    -----
    Records are not stored on the graph; they live in :attr:`records`. Channels are
    derived from record type ("snapshot", "patch", "fragment").

    Call Stack Persistence
    -----------------------
    The call stack is persisted via two mechanisms:

    1. **Direct serialization** (fast path)

       * :attr:`call_stack` serializes with ledger JSON.
       * Used for REST resume, save/load at the current state.
       * No stream replay needed.
       * Source of truth when :attr:`event_sourced` is ``False``.

    2. **Event-sourced snapshots** (time-travel path)

       * :class:`~tangl.vm.stack_snapshot.StackSnapshot` records emitted to the
         stream after each step.
       * Used for undo or replay to arbitrary historical states.
       * Source of truth when :attr:`event_sourced` is ``True``.
       * Enables validation via checksum comparison.
       * Produced by :meth:`record_stack_snapshot`; consumed by
         :meth:`recover_stack_from_stream` and
         :meth:`~tangl.core.record.StreamRegistry.iter_channel` with
         ``channel="stack"``.

    Usage Patterns
    --------------
    REST interface (fast resume)::

        ledger = Ledger.structure(json_data)  # trusts call_stack in JSON
        assert ledger.event_sourced is False
        # call_stack restored directly, no stream replay

    Event-sourced rebuild (time-travel)::

        ledger = Ledger.structure(json_data)
        ledger.event_sourced = True
        # Rebuilds call_stack from StackSnapshot records
        stack = Ledger.recover_stack_from_stream(ledger.records, ledger.graph)

    Undo to step ``N``::

        ledger.undo_to_step(42)
        # Both graph and call_stack reconstructed to consistent state

    Why two paths
    -------------
    Event-sourced systems and request/response flows have different persistence
    needs:

    * **REST**: Execution spans HTTP requests; fast resume should not require
      replay.
    * **Undo**: Time-travel requires consistent historical graph and stack
      state.
    * **Validation**: Stream history serves as an audit trail and checksum for
      serialized state.

    **Domains:** Only singleton domains belong at the ledger level. They
    serialize via the usual :meth:`structure`/:meth:`unstructure` hooks for
    singletons; other domain styles are not supported here and should live on
    graph items where scope discovery can rehydrate them dynamically.
    """
    graph: Graph
    cursor_id: UUID = None
    step: int = 0
    records: StreamRegistry = Field(default_factory=StreamRegistry)
    snapshot_cadence: int = 1
    event_sourced: bool = False
    user: Optional[User] = Field(None, exclude=True)
    cursor_history: list[UUID] = Field(default_factory=list)
    call_stack: list[StackFrame] = Field(default_factory=list)
    """
    Runtime call stack for subroutine jumps.

    Included in the serialized ledger payload for save/resume flows; time-travel
    still reconstructs call stacks from stream snapshots when needed.
    """

    def push_snapshot(self):
        # No particular need to unstructure/serialize this separately from
        # everything else on the stream
        # todo: if event sourced, we need to update the graph before snapshot
        snapshot = Snapshot.from_item(self.graph)
        self.records.add_record(snapshot)

    def maybe_push_snapshot(self, snapshot_cadence=None, force=False):
        # Use force if you want to insist on a snapshot
        snapshot_cadence = snapshot_cadence if snapshot_cadence is not None else self.snapshot_cadence
        if (self.step % snapshot_cadence == 0) or force:
            self.push_snapshot()

    def record_stack_snapshot(self) -> None:
        """Persist the current call stack as a :class:`StackSnapshot`."""

        from .stack_snapshot import StackFrameSnapshot

        snapshot = StackSnapshot(
            frames=[
                StackFrameSnapshot(
                    return_cursor_id=frame.return_cursor_id,
                    call_type=frame.call_type,
                )
                for frame in self.call_stack
            ]
        )
        self.records.add_record(snapshot)

    @classmethod
    def recover_graph_from_stream(
        cls,
        records: StreamRegistry,
        *,
        verify_patches: bool = True,
    ) -> Graph:
        """Restore a graph from snapshots and patches in ``records``.

        Parameters
        ----------
        records:
            Stream of snapshots and patches to replay.
        verify_patches:
            When ``False``, bypass registry state hash checks on patches. Undo
            operations use this to tolerate partial streams while still applying
            historical mutations in order.
        """

        # Get the most recent snapshot
        snapshot = records.last(channel="snapshot")  # type: Snapshot[Graph]
        if snapshot is None:
            raise RuntimeError(f"No snapshot found in record stream")
        graph = snapshot.restore_item()  # don't access item directly
        seq = snapshot.seq
        # Get all patches since the most recent snapshot and apply them
        patches = records.find_all(
            # is_instance=Patch,
            predicate=lambda x: x.seq > seq,
            has_channel="patch",
            sort_key=lambda x: x.seq,
        )  # type: list[Patch]
        # fine if this is [], just returns graph from snapshot
        for patch in patches:
            patch_to_apply = patch
            if not verify_patches:
                patch_to_apply = patch.model_copy(update={"registry_state_hash": None})

            graph = patch_to_apply.apply(graph)
        return graph

    def get_journal(self, marker_name: str):
        # todo: should default to most recent -1 or something
        return self.records.get_section(marker_name, marker_type="journal", has_channel="fragment")

    def get_frame(self) -> Frame:
        from .dispatch import vm_dispatch
        return Frame(
            graph=self.graph,
            cursor_id=self.cursor_id,
            step=self.step,
            records=self.records,
            event_sourced=self.event_sourced,
            cursor_history=self.cursor_history,
            call_stack=self.call_stack,
        )

    @property
    def turn(self) -> int:
        """Number of position changes represented in ``cursor_history``."""

        return self._compute_turn(self.cursor_history)

    @staticmethod
    def _compute_turn(history: list[UUID]) -> int:
        """Count distinct position changes, ignoring self-loops."""

        if not history:
            return 0

        turn = 1

        for index in range(1, len(history)):
            if history[index] != history[index - 1]:
                turn += 1

        return turn

    def init_cursor(self) -> None:
        """Enter the current cursor to bootstrap the ledger journal."""

        start_node = self.graph.get(self.cursor_id)
        if start_node is None:
            raise RuntimeError(f"Initial cursor {self.cursor_id} not found in graph")

        frame = self.get_frame()

        frame.jump_to_node(start_node)

        self.cursor_id = frame.cursor_id
        self.step = frame.step

    # todo: should probably add this as a general pattern for structuring/unstructuring
    #       entity-typed model fields using introspection (see registry)

    @classmethod
    def structure(cls, data: Mapping[str, Any], **kwargs) -> "Ledger":
        payload = dict(data)
        graph_data = payload.pop("graph", None)
        # domain_data = payload.pop("domains", None)
        record_data = payload.pop("records", None)
        call_stack_data = payload.pop("call_stack", None)
        if "graph" not in payload:
            payload["graph"] = Graph()
        ledger = super().structure(payload, **kwargs)

        if graph_data is not None:
            ledger.graph = Graph.structure(graph_data)

        # if domain_data is not None:
        #     ledger.domains = [Domain.structure(item) for item in domain_data]
        # else:
        #     ledger.domains = []

        if record_data is not None:
            raw_records = list(record_data.get("_data", []))
            for entry in raw_records:
                item_payload = entry.get("item") if isinstance(entry, Mapping) else None
                if isinstance(item_payload, Mapping):
                    obj_cls = item_payload.get("obj_cls")
                    if obj_cls in {Graph, Graph.__name__, Graph.__qualname__}:
                        entry["item"] = Graph.structure(dict(item_payload))
            ledger.records = StreamRegistry.structure(record_data)
        else:
            ledger.records = StreamRegistry()

        if ledger.event_sourced and (graph_data is None or not getattr(ledger.graph, "data", {})):
            ledger.graph = cls.recover_graph_from_stream(ledger.records)

        if ledger.event_sourced:
            ledger.call_stack = cls.recover_stack_from_stream(
                ledger.records,
                ledger.graph,
            )
            if call_stack_data and ledger.call_stack:
                serialized_depth = len(call_stack_data)
                reconstructed_depth = len(ledger.call_stack)
                if serialized_depth != reconstructed_depth:
                    logger.warning(
                        "Serialized call stack depth %s does not match reconstructed depth %s",
                        serialized_depth,
                        reconstructed_depth,
                    )
        elif call_stack_data:
            ledger.call_stack = [
                StackFrame.model_validate(frame_data) for frame_data in call_stack_data
            ]

        return ledger

    @classmethod
    def recover_stack_from_stream(
        cls,
        records: StreamRegistry,
        graph: Graph,
        upto_seq: int | None = None,
    ) -> list[StackFrame]:
        """Rebuild a call stack from :class:`StackSnapshot` records."""

        predicate = None
        if upto_seq is not None:
            predicate = lambda record: record.seq <= upto_seq

        snapshots = list(
            records.find_all(
                has_channel="stack",
                predicate=predicate,
                sort_key=lambda record: record.seq,
            )
        )

        if not snapshots:
            return []

        snapshot = snapshots[-1]
        stack: list[StackFrame] = []

        for depth, frame_snapshot in enumerate(snapshot.frames):
            caller_node = graph.get(frame_snapshot.return_cursor_id)
            call_site_label = caller_node.label if caller_node is not None else "unknown"
            frame = StackFrame(
                return_cursor_id=frame_snapshot.return_cursor_id,
                call_site_label=call_site_label,
                call_type=frame_snapshot.call_type,
                depth=depth,
            )
            stack.append(frame)

        return stack

    def undo_to_step(self, target_step: int) -> None:
        """Rewind ledger state to ``target_step`` using event-sourced history."""

        if not self.event_sourced:
            raise RuntimeError("undo_to_step requires event_sourced=True")

        if target_step <= 0 or target_step >= self.step:
            raise ValueError(
                f"target_step {target_step} must be > 0 and less than current step {self.step}"
            )

        snapshots = list(self.records.find_all(has_channel="stack"))
        if len(snapshots) < target_step:
            raise KeyError(f"No stack snapshot recorded for step {target_step}")

        target_snapshot = snapshots[target_step - 1]
        truncated = self.records.slice_to_seq(target_snapshot.seq)
        self.graph = self.recover_graph_from_stream(
            truncated, verify_patches=False
        )
        self.call_stack = self.recover_stack_from_stream(
            truncated, self.graph, upto_seq=target_snapshot.seq
        )

        if self.cursor_history and target_step - 1 < len(self.cursor_history):
            self.cursor_history = self.cursor_history[:target_step]
            self.cursor_id = self.cursor_history[-1]

        self.step = target_step

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        graph_payload = self.graph.unstructure()
        graph_payload.pop("data", None)
        data["graph"] = graph_payload

        # data["domains"] = [domain.unstructure() for domain in self.domains]

        records_payload = self.records.unstructure()
        sanitized_records: list[UnstructuredData] = []
        for record in self.records.data.values():
            record_payload = record.unstructure()
            item = getattr(record, "item", None)
            if hasattr(item, "unstructure"):
                item_payload = item.unstructure()
                if isinstance(item_payload, dict):
                    item_payload.pop("data", None)
                record_payload["item"] = item_payload
            sanitized_records.append(record_payload)
        records_payload["_data"] = sanitized_records
        data["records"] = records_payload

        if self.event_sourced:
            data["graph"] = {
                "uid": self.graph.uid,
                "label": self.graph.label,
            }

        return data
