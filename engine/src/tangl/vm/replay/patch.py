# tangl/vm/replay/patch.py
# language=rst
"""
Replay artifacts: Patch and Snapshot.

A :class:`Patch` is a frozen sequence of canonicalized events that can be
applied to a registry to reproduce mutations. A :class:`Snapshot` materializes
a registry's state for fast recovery, trading a bit of storage for speed.
"""
from __future__ import annotations
from typing import Optional, Literal, Iterable, TypeVar, Generic
from uuid import UUID

from pydantic import field_validator

from tangl.type_hints import Hash
from tangl.core import Record, Registry, Entity
from tangl.utils.hashing import hashing_func
from .event import Event

# todo: may want to use different patch formats:
#       - canonicalized events
#       - raw event sequence (for audit)
#       - dict-diff (update delta)

class Patch(Record):
    # language=rst
    """
    Patch(registry_id: UUID | None, registry_state_hash: bytes | None, events: list[Event])

    Frozen record of canonicalized events that can replay mutations on a registry.

    Why
    ----
    Captures a minimal, replayable history of state changes for a registry or graph.
    A patch ensures deterministic reconstruction by verifying that the target
    registry’s id and base state hash match before applying its events.

    Key Features
    ------------
    * **Immutable** – patches are frozen once created; replay is pure and idempotent.
    * **Guarded apply** – validates target registry id and state hash before mutation.
    * **Canonical events** – events sorted and deduplicated by
      :meth:`~tangl.vm.replay.event.Event.canonicalize_events`.
    * **Integration** – works with :class:`~tangl.core.registry.Registry` and ledger
      recovery to rebuild current state from snapshots.

    API
    ---
    - :attr:`registry_id` – optional UUID guard ensuring patch applies to the right registry.
    - :attr:`registry_state_hash` – optional guard verifying the base state hash.
    - :attr:`events` – ordered, canonicalized list of :class:`~tangl.vm.replay.event.Event`.
    - :meth:`apply(registry)` – validate guards and replay all events, returning the mutated registry.

    Notes
    -----
    Patches are typically appended to the ledger between snapshots for efficient
    incremental recovery.  Use :meth:`Event.canonicalize_events` to build canonical
    patches suitable for deduplication and audit.
    """
    registry_id: Optional[UUID] = None
    registry_state_hash: Hash = None
    events: list[Event]

    @field_validator("events")
    @classmethod
    def _canonicalize_events(cls, data) -> Iterable[Event]:
        # may want an option just sort by seq instead
        return Event.canonicalize_events(data)

    def apply(self, registry: Registry) -> Registry:
        if self.registry_id and self.registry_id != registry.uid:
            raise ValueError(f"Wrong registry for patch {registry.uid} != {self.registry_id}")
        if self.registry_state_hash:
            current_hash = registry._state_hash()
            valid_hashes = {current_hash, hashing_func(current_hash)}
            if self.registry_state_hash not in valid_hashes:
                raise ValueError(f"Wrong registry state hash for patch")

        return Event.apply_all(self.events, registry)
