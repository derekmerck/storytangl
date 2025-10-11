# tangl/vm/ledger.py
"""
State holder for the live graph, cursor, and record stream (snapshots, patches, journal).
"""
from typing import TYPE_CHECKING
from pydantic import Field
from uuid import UUID

from tangl.core import Entity, Graph, Node, Domain, Record, StreamRegistry, Snapshot
from tangl.type_hints import StringMap
from .frame import Frame

if TYPE_CHECKING:
    from .replay import Patch

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

    **Domains:** Only singleton domains belong at the ledger level. They
    serialize via the usual :meth:`structure`/:meth:`unstructure` hooks for
    singletons; other domain styles are not supported here and should live on
    graph items where scope discovery can rehydrate them dynamically.
    """
    graph: Graph = None
    cursor_id: UUID = None
    step: int = -1
    domains: list[Domain] = Field(default_factory=list)  # ledger-level singletons only
    records: StreamRegistry = Field(default_factory=StreamRegistry)
    snapshot_cadence: int = 1

    def push_snapshot(self):
        # No particular need to unstructure/serialize this separately from
        # everything else on the stream
        snapshot = Snapshot.from_item(self.graph)
        self.records.add_record(snapshot)

    def maybe_push_snapshot(self, snapshot_cadence=None, force=False):
        # Use force if you want to insist on a snapshot
        snapshot_cadence = snapshot_cadence if snapshot_cadence is not None else self.snapshot_cadence
        if (self.step % snapshot_cadence == 0) or force:
            self.push_snapshot()

    @classmethod
    def recover_graph_from_stream(cls, records: StreamRegistry) -> Graph:

        # Get the most recent snapshot
        snapshot = records.last(channel="snapshot")  # type: Snapshot[Graph]
        if snapshot is None:
            raise RuntimeError(f"No snapshot found in record stream")
        graph = snapshot.restore_item()  # don't access item directly
        seq = snapshot.seq
        # Get all patches since the most recent snapshot and apply them
        patches = records.find_all(
            predicate=lambda x: x.seq > seq,
            has_channel="patch",
            sort_key=lambda x: x.seq)  # type: list[Patch]
        # fine if this is [], just returns graph from snapshot
        for p in patches:
            graph = p.apply(graph)
        return graph

    def get_journal(self, marker_name: str):
        # todo: should default to most recent -1 or something
        return self.records.get_section(marker_name, has_channel="fragment")

    def get_frame(self) -> Frame:
        return Frame(graph = self.graph,
                     cursor_id = self.cursor_id,
                     records = self.records)

    @classmethod
    def structure(cls, data: StringMap) -> "Ledger":
        payload = dict(data)

        graph_data = payload.pop("graph", None)
        if isinstance(graph_data, dict):
            payload["graph"] = Graph.structure(graph_data)

        records_data = payload.pop("records", None)
        if isinstance(records_data, dict):
            payload["records"] = StreamRegistry.structure(records_data)

        domains_data = payload.pop("domains", None)
        if isinstance(domains_data, list):
            payload["domains"] = [Domain.structure(item) for item in domains_data]

        return super().structure(payload)

    def unstructure(self) -> StringMap:
        data = super().unstructure()
        data["graph"] = self.graph.unstructure()
        data["records"] = self.records.unstructure()
        data["domains"] = [domain.unstructure() for domain in self.domains]
        return data


