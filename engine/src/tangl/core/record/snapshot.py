from __future__ import annotations
from typing import Generic, Literal, Optional, TypeVar
import logging
from copy import deepcopy

from tangl.core.entity import Entity
from tangl.type_hints import Hash
from .content_addressable import ContentAddressable
from .record import Record

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

EntityT = TypeVar('EntityT', bound=Entity)

class Snapshot(Record, ContentAddressable, Generic[EntityT]):
    # language=rst
    """
    Snapshot[EntityT]()

    Frozen record capturing a deep copy of an entity for persistence and recovery.

    Why
    ----
    Provides a stable, hash-verified baseline for reconstruction or audit. Used by
    the ledger to persist materialized graph state and restore it deterministically
    before applying subsequent patches.

    Key Features
    ------------
    * **Immutable baseline** – deep copy of an entity at a point in time.
    * **State hash** – :attr:`item_state_hash` verifies integrity during recovery.
    * **Generic type parameter** – documents the entity type being snapshotted.
    * **Integration** – works with :class:`~tangl.vm.ledger.Ledger` and
      :class:`~tangl.vm.replay.patch.Patch` for replay and restoration.

    API
    ---
    - :meth:`from_item(item)` – create a snapshot with a deep copy and computed hash.
    - :meth:`restore_item()` – return a deep copy of the stored entity.
    - :attr:`item_state_hash` – hash of the entity’s state for verification.

    Example
    -------
    >>> snap = Snapshot.from_item(graph)
    >>> stream.add_record(snap)
    >>> restored = stream.last(channel="snapshot").restore_item()

    Notes
    -----
    Snapshots are immutable records; they do not serialize data internally but rely
    on higher-level persistence managers to handle storage. Type parameters exist
    for documentation only.
    """
    item: EntityT  #: :meta-private:

    @classmethod
    def from_item(cls, item: EntityT) -> Snapshot[EntityT]:
        # No need to unstructure or serialize here, that can be handled by the
        # general persistence manager like anything else.
        return cls(item=deepcopy(item), content_hash=item._state_hash())

    def restore_item(self, verify: bool = False) -> EntityT:
        item = deepcopy(self.item)
        if verify and item._state_hash() != self.content_hash:
            raise RuntimeError("Recovered item state does not match item state hash.")
        return item


Snapshot.model_rebuild()

