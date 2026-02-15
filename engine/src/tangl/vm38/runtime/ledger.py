from uuid import UUID
from typing import Optional, Self

from pydantic import Field

from tangl.type_hints import UnstructuredData
from tangl.core38 import Graph, OrderedRegistry, Entity, Snapshot, Selector
from tangl.vm38.traversable import TraversableNode, TraversableEdge
from .frame import Frame

class Ledger(Entity):
    # Owning boundary for user, graph, and output
    # - unstructure needs to deal with the graph and the output_stream
    graph: Graph
    output_stream: OrderedRegistry = Field(default_factory=OrderedRegistry)

    # - The cursor and return stack of edges to prior cursors are stored as UUIDs
    cursor_id: UUID

    @property
    def cursor(self) -> TraversableNode:
        return self.graph.get(self.cursor_id)

    @cursor.setter
    def cursor(self, value: TraversableNode):
        if value is not None:
            self.cursor_id = value

    call_stack_ids: list[UUID] = Field(default_factory=list)

    def _call_stack(self) -> list[TraversableEdge]:
        # do not push directly!  This is marked private b/c it's just
        # for introspection of the actual members, use push_call and
        # pop_call.
        return [self.graph.get(e) for e in self.call_stack_ids]

    def push_call(self, edge: TraversableEdge):
        if not edge.return_phase is not None:
            raise ValueError("Putting a call onto the stack requires a return phase/type")
        self.call_stack_ids.append(edge.uid)

    def pop_call(self) -> TraversableEdge:
        # don't forget to reverse it to follow it back
        call_edge_id = self.call_stack_ids.pop()
        return self.graph.get(call_edge_id)  # type: TraversableEdge

    # - cursor counters for tracking traversal distance (pass these into frame ctx for game rounds, turns passed, etc.)
    reentrant_steps: int = -1  # number of times logic reentered the current cursor without exit
    cursor_steps: int = -1      # total number of cursor updates (non-reentrant follows)
    choice_steps: int = -1      # total number of choice resolutions

    # - User is attached/detached by the persistence layer
    user: Optional[Entity] = Field(None, exclude=True)
    # - convenience for checking persistence layer assumptions
    user_id: Optional[UUID] = None

    def get_frame(self) -> Frame:
        return Frame(self.graph, self.cursor, self.output_stream, self.get_return_stack())

    def resolve_choice(self, edge_id: UUID):
        edge = self.graph.get(edge_id)
        frame = self.get_frame()
        frame.resolve_choice(edge)
        # update the cursor and return stack
        self.choice_steps += 1
        self.cursor_steps += frame.cursor_steps
        self.cursor_id = frame.cursor.uid  # since this is a property, it might passthru updates directly?
        self.return_stack_ids = [e.uid for e in frame.return_stack]
        self.save_snapshot()

    def save_snapshot(self):
        snapshot = Snapshot(payload=self)
        self.output_stream.append(snapshot)

    # Creation
    # --------

    def initialize_ledger(self, entry_id: UUID):
        entry_node = self.graph.get(entry_id)
        frame = self.get_frame()
        frame.goto_node(entry_node)
        # update the cursor and return stack
        self.cursor_steps += frame.cursor_steps
        self.cursor_id = frame.cursor.uid  # since this is a property, it might passthru updates directly?
        self.return_stack_ids = [e.uid for e in frame.return_stack]
        self.save_snapshot()

    @classmethod
    def from_graph(cls, graph: Graph, entry_id: UUID):
        inst = cls(graph=graph)
        inst.initialize_ledger(entry_id)
        return inst

    def unstructure(self):
        data = super().unstructure()
        data['graph'] = self.graph.unstructure()
        data['output_stream'] = self.output_stream.unstructure()

    @classmethod
    def structure(cls, data: UnstructuredData, _ctx=None) -> Self:
        data['graph'] = Graph.structure(data['graph'], _ctx=_ctx)
        data['output_stream'] = Graph.structure(data['output_stream'], _ctx=_ctx)
        return super().structure(data, _ctx=_ctx)

    @classmethod
    def restore(cls, stream_registry: OrderedRegistry, base, restore):
        base_snapshot = stream_registry.find_last(Selector(has_kind=Snapshot, seq_before=base))
        patches = stream_registry.find_all(Selector(has_seq_in=(base, restore)))  # between base and restore point
        inst = base_snapshot.materialize()
        for patch in patches:
            patch.apply_to(inst)
        return inst

