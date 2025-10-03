# tangl/vm/ledger.py
from pydantic import Field
from copy import deepcopy
from uuid import UUID

from tangl.core import Entity, Graph, Node, Domain
from tangl.core.record import Record, StreamRegistry
from .frame import Frame

class Ledger(Entity):
    """
    - has graph/state, cursor, record stream/history, meta domains (user)
    - patches/snapshots are filtered views of event-sourcing items on the record stream
    - journal (output) is a filtered view of rendered content fragments on the record stream
    - frame is an ephemeral workspace with a view of the graph and scoped capabilities for
        resolving a step, it can push records onto the ledger's record stream

    Channel names can be inferred from the record type:
    - snapshot for Record(type=snapshot)
    - patch for Record(type=patch)
    - fragment for Record(type=fragment)

    Marker types:
    - frame, named step-xxxx on follow_edge()
    """
    graph: Graph = None
    cursor_id: UUID = None
    step: int = -1
    domains: list[Domain] = Field(default_factory=list)
    records: StreamRegistry = Field(default_factory=StreamRegistry)
    snapshot_cadence: int = 1

    def push_snapshot(self):
        # No particular need to unstructure/serialize this separately from
        # everything else on the stream
        snapshot = Record(type='snapshot', data=deepcopy(self.graph))
        self.records.add_record(snapshot)

    def maybe_push_snapshot(self, snapshot_cadence=None, force=False):
        # Use force if you want to insist on a snapshot
        snapshot_cadence = snapshot_cadence if snapshot_cadence is not None else self.snapshot_cadence
        if (self.step % snapshot_cadence == 0) or force:
            self.push_snapshot()

    @classmethod
    def recover_graph_from_stream(cls, records: StreamRegistry) -> Graph:
        # If this is event sourced, we aren't persisting the graph attrib and might
        # point to this with a cached property

        # Get the most recent snapshot
        snapshot = records.last(channel="snapshot")
        if snapshot is None:
            graph = Graph()
            seq = -1
        else:
            graph = snapshot.data   # type: Graph
            seq = snapshot.seq
        # Get all patches since the most recent snapshot and apply them
        patches = records.find_all(
            predicate=lambda x: x.seq > seq,
            channel="patch")
        for p in patches:
            p.apply(graph)
        return graph

    def get_journal(self, marker_name: str):
        # todo: should default to most recent -1 or something
        return self.records.get_section(marker_name, has_channel="fragment")

    def get_frame(self) -> Frame:
        return Frame(graph = self.graph,
                     cursor_id = self.cursor_id,
                     records = self.records)


