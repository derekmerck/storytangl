# tangl/vm38/runtime/ledger.py
"""Persistent session state for a single traversal.

The Ledger owns long-lived state that persists across player actions:
the graph, cursor position and history, return stack, and accumulated output.
"""

from __future__ import annotations

from typing import Optional, Self
from uuid import UUID

from pydantic import Field

from tangl.core38 import Entity, Graph, OrderedRegistry, Selector, Snapshot
from tangl.type_hints import UnstructuredData
from tangl.vm38.traversable import TraversableEdge, TraversableNode

from .frame import Frame
from ..fragments import Fragment


__all__ = ["Ledger"]


class Ledger(Entity):
    """Persistent traversal state across player actions."""

    graph: Graph
    output_stream: OrderedRegistry = Field(default_factory=OrderedRegistry)

    cursor_id: UUID
    cursor_history: list[UUID] = Field(default_factory=list)

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
        from tangl.vm38.traversal import count_turns

        return count_turns(self.cursor_history)

    @property
    def step(self) -> int:
        """Alias for ``cursor_steps``."""
        return self.cursor_steps

    @step.setter
    def step(self, value: int) -> None:
        self.cursor_steps = value

    call_stack_ids: list[UUID] = Field(default_factory=list)

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

    def model_post_init(self, __context) -> None:
        """Seed cursor history with initial cursor position."""
        if not self.cursor_history and self.cursor_id is not None:
            self.cursor_history.append(self.cursor_id)

    def get_frame(self) -> Frame:
        """Create an ephemeral frame for the next pipeline execution."""
        return Frame(
            self.graph,
            self.cursor,
            self.output_stream,
            self._call_stack(),
        )

    def resolve_choice(self, edge_id: UUID) -> None:
        """Resolve a player choice and sync frame results into ledger state."""
        edge = self.graph.get(edge_id)
        if edge is None:
            raise ValueError(f"Choice edge not found: {edge_id}")

        frame = self.get_frame()
        frame.resolve_choice(edge)

        for call_edge in frame.return_stack:
            if call_edge is None:
                raise ValueError("Frame return stack contains a null edge")

        self.choice_steps += 1
        self.cursor_steps += frame.cursor_steps
        self.cursor_id = frame.cursor.uid
        self.cursor_history.append(self.cursor_id)
        self.call_stack_ids = [edge.uid for edge in frame.return_stack]

    def get_journal(self, *, since_step: int = 0, limit: int = 0) -> list[Fragment]:
        """Return output fragments in chronological order, optionally filtered."""
        selector = Selector(has_kind=Fragment)
        fragments: list[Fragment] = []

        for record in selector.filter(self.output_stream):
            if record.step >= since_step or record.step < 0:
                fragments.append(record)

        if limit > 0 and len(fragments) > limit:
            fragments = fragments[-limit:]

        return fragments

    def unstructure(self) -> UnstructuredData:
        """Serialize ledger state to plain data for persistence."""
        return {
            "uid": str(self.uid),
            "label": self.label,
            "cursor_id": str(self.cursor_id),
            "cursor_history": [str(uid) for uid in self.cursor_history],
            "cursor_steps": self.cursor_steps,
            "choice_steps": self.choice_steps,
            "reentrant_steps": self.reentrant_steps,
            "call_stack_ids": [str(uid) for uid in self.call_stack_ids],
            "user_id": str(self.user_id) if self.user_id else None,
            "graph": self.graph.unstructure(),
            "output_stream": self.output_stream.unstructure(),
        }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        """Reconstruct a ledger from serialized data."""
        graph = Graph.structure(data["graph"])
        output_stream = OrderedRegistry.structure(data.get("output_stream", {}))

        return cls(
            uid=UUID(data["uid"]),
            label=data.get("label", ""),
            graph=graph,
            output_stream=output_stream,
            cursor_id=UUID(data["cursor_id"]),
            cursor_history=[UUID(uid) for uid in data.get("cursor_history", [])],
            cursor_steps=data.get("cursor_steps", -1),
            choice_steps=data.get("choice_steps", -1),
            reentrant_steps=data.get("reentrant_steps", -1),
            call_stack_ids=[UUID(uid) for uid in data.get("call_stack_ids", [])],
            user_id=UUID(data["user_id"]) if data.get("user_id") else None,
        )

    def save_snapshot(self, *, force: bool = False, cadence: int = 0) -> Optional[Snapshot]:
        """Save a snapshot if forced or cadence says one is due."""
        should_save = force or (
            cadence > 0
            and self.choice_steps >= 0
            and (self.choice_steps % cadence) == 0
        )
        if not should_save:
            return None

        snapshot = Snapshot.from_entity(self)
        self.output_stream.append(snapshot)
        return snapshot
