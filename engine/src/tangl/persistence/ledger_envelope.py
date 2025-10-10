from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LedgerEnvelope(BaseModel):
    """Serialization wrapper for :class:`~tangl.vm.ledger.Ledger` state."""

    model_config = ConfigDict(extra="ignore")

    ledger_uid: UUID
    graph: dict[str, Any]
    cursor_id: UUID
    step: int = -1
    records: dict[str, Any]
    domain_names: list[str] = Field(default_factory=list)
    snapshot_cadence: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "LedgerEnvelope":
        """Create an envelope from a :class:`~tangl.vm.ledger.Ledger`."""

        from tangl.vm.ledger import Ledger

        domain_names = [domain.get_label() for domain in ledger.domains]

        last_snapshot = ledger.records.last(channel="snapshot")
        last_snapshot_seq = last_snapshot.seq if last_snapshot else -1

        return cls(
            ledger_uid=ledger.uid,
            graph=ledger.graph.unstructure(),
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            records=cls._unstructure_records(ledger.records),
            domain_names=domain_names,
            snapshot_cadence=ledger.snapshot_cadence,
            metadata={
                "last_snapshot_seq": last_snapshot_seq,
                "schema_version": "v37",
            },
        )

    @staticmethod
    def _unstructure_records(records: "StreamRegistry") -> dict[str, Any]:
        """Convert a :class:`~tangl.core.record.StreamRegistry` into JSON-friendly data."""

        from tangl.core import StreamRegistry

        if not isinstance(records, StreamRegistry):  # defensive for malformed inputs
            raise TypeError("records must be a StreamRegistry")

        raw = records.unstructure()
        normalized: list[dict[str, Any]] = []

        for record, payload in zip(records, raw.get("_data", [])):
            entry = dict(payload)

            if hasattr(record, "item") and record.record_type == "snapshot":
                entry["item"] = record.item.unstructure()

            if hasattr(record, "events"):
                entry["events"] = [event.unstructure() for event in record.events]

            normalized.append(entry)

        raw["_data"] = normalized
        return raw

    def to_ledger(self, event_sourced: bool = False) -> "Ledger":
        """Hydrate a :class:`~tangl.vm.ledger.Ledger` from the envelope."""

        from tangl.core import Domain, Graph, StreamRegistry
        from tangl.vm.ledger import Ledger

        records = StreamRegistry.structure(self.records)

        if event_sourced:
            graph = self._rebuild_graph_from_records(records)
        else:
            graph = Graph.structure(self.graph)

        domains = [Domain.structure({"label": name}) for name in self.domain_names]

        return Ledger(
            uid=self.ledger_uid,
            graph=graph,
            cursor_id=self.cursor_id,
            step=self.step,
            records=records,
            domains=domains,
            snapshot_cadence=self.snapshot_cadence,
        )

    def _rebuild_graph_from_records(self, records: "StreamRegistry") -> "Graph":
        from tangl.core import Graph, Snapshot

        if isinstance(self.records, dict):
            raw_entries = self.records.get("_data", [])
        else:
            raw_entries = records.unstructure().get("_data", [])
        snapshot_idx: int | None = None
        for idx, entry in enumerate(raw_entries):
            if isinstance(entry, dict) and entry.get("record_type") == "snapshot":
                snapshot_idx = idx
        if snapshot_idx is None:
            raise RuntimeError("No snapshot available for event-sourced recovery")

        snapshot_entry = raw_entries[snapshot_idx]
        item_data = snapshot_entry.get("item") if isinstance(snapshot_entry, dict) else None
        if not isinstance(item_data, dict):
            raise RuntimeError("Snapshot item missing graph payload")

        graph = Graph.structure(dict(item_data))

        structured_records = list(records)
        for idx, record in enumerate(structured_records):
            if idx <= snapshot_idx:
                continue
            if isinstance(record, Snapshot):
                continue
            if getattr(record, "record_type", None) == "patch":
                graph = record.apply(graph)

        return graph

    @property
    def uid(self) -> UUID:
        """Expose :attr:`ledger_uid` for persistence managers expecting ``uid``."""

        return self.ledger_uid
