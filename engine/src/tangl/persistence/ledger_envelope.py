from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LedgerEnvelope(BaseModel):
    """Serialization wrapper for :class:`~tangl.vm.ledger.Ledger` state."""

    model_config = ConfigDict(extra="ignore")

    ledger_uid: UUID
    ledger: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "LedgerEnvelope":
        """Create an envelope from a :class:`~tangl.vm.ledger.Ledger`."""

        from tangl.vm.ledger import Ledger

        last_snapshot = ledger.records.last(channel="snapshot")
        last_snapshot_seq = last_snapshot.seq if last_snapshot else -1

        ledger_payload = ledger.unstructure()

        return cls(
            ledger_uid=ledger.uid,
            ledger=ledger_payload,
            metadata={
                "last_snapshot_seq": last_snapshot_seq,
                "schema_version": "v37",
            },
        )

    def to_ledger(self, event_sourced: bool = False) -> "Ledger":
        """Hydrate a :class:`~tangl.vm.ledger.Ledger` from the envelope."""

        from tangl.vm.ledger import Ledger

        ledger = Ledger.structure(self.ledger)

        if ledger.uid != self.ledger_uid:
            ledger = ledger.model_copy(update={"uid": self.ledger_uid})

        if event_sourced:
            ledger.graph = Ledger.recover_graph_from_stream(ledger.records)

        return ledger

    @property
    def uid(self) -> UUID:
        """Expose :attr:`ledger_uid` for persistence managers expecting ``uid``."""

        return self.ledger_uid
