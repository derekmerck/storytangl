# tangl/vm/ledger.py
"""
State holder for the live graph, cursor, and record stream (snapshots, patches, journal).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, Iterable
from pydantic import Field
from uuid import UUID

from tangl.type_hints import UnstructuredData
from tangl.core import Entity, Graph, StreamRegistry, Snapshot, BehaviorRegistry
from .frame import Frame

if TYPE_CHECKING:
    from tangl.service.user.user import User
    from .replay import Patch
else:
    User = Entity

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
    graph: Graph
    cursor_id: UUID = None
    step: int = 0
    records: StreamRegistry = Field(default_factory=StreamRegistry)
    snapshot_cadence: int = 1
    event_sourced: bool = False
    user: Optional[User] = Field(None, exclude=True)

    # todo: could include the author_domain here, as long as it is a SINGLETON type
    #       behavior registry, maybe better to keep the world and get the author
    #       domain from that?
    #       since it serializes, should ONLY admit singleton dispatch as injected layer

    def get_active_layers(self) -> Iterable[BehaviorRegistry]:
        from tangl.vm.dispatch import vm_dispatch
        # todo: should pass story-dispatch in on creation, violates looking
        #       into application domain subpackages, or collect it from a
        #       'story graph' object that also includes the author dispatch
        # from tangl.story.dispatch import story_dispatch
        # return vm_dispatch, story_dispatch
        return vm_dispatch,

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
            # is_instance=Patch,
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
        from .dispatch import vm_dispatch
        return Frame(
            graph=self.graph,
            cursor_id=self.cursor_id,
            step=self.step,
            records=self.records,
            event_sourced=self.event_sourced,
            active_layers=[vm_dispatch]
        )

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

        return ledger

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
