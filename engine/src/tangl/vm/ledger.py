# tangl/vm/ledger.py
from pydantic import Field

from tangl.core import Entity, Graph, Node, Domain
from tangl.core.record import Record, RecordStream

Frame = object

class Ledger(Entity):
    """
    - has graph/state, cursor, record stream/history, meta domains (user)
    - patches/snapshots are filtered views of event-sourcing items on the record stream
    - journal (output) is a filtered view of rendered content fragments on the record stream
    - frame is an ephemeral workspace with a view of the graph and scoped capabilities for
        resolving a step, it can push records onto the ledger's record stream
    """
    graph: Graph = None
    cursor: Node = None
    step: int = -1
    domains: list[Domain] = Field(default_factory=list)
    records: RecordStream = Field(default_factory=RecordStream)

    def get_journal(self, marker_name: str):
        return self.records.get_section(marker_name, has_channel="journal")

    def get_frame(self) -> Frame:
        return Frame(graph = self.graph,
                     cursor = self.cursor,
                     records = self.records)

