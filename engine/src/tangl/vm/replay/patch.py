# tangl/vm/replay/patch.py
from __future__ import annotations
from typing import Optional, Literal, Iterable, TypeVar, Generic
from uuid import UUID
from copy import deepcopy

from pydantic import field_validator

from tangl.type_hints import Hash
from tangl.core import Record, Registry, Entity
from .events import Event

# todo: may want to use different patch formats:
#       - canonicalized events
#       - raw event sequence (for audit)
#       - dict-diff (update delta)

class Patch(Record):
    """
    Patch(registry_id: ~uuid.UUID, registry_state_hash: bytes, events: list[Event])
    """
    record_type: Literal['patch'] = 'patch'
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
        if self.registry_state_hash and self.registry_state_hash != registry._state_hash():
            raise ValueError(f"Wrong registry state hash for patch")

        return Event.apply_all(self.events, registry)

EntityT = TypeVar('EntityT', bound=Entity)

class Snapshot(Record, Generic[EntityT]):
    """
    Snapshot[EntityT]()

    Don't set or get item directly unless you know what you're doing.
    Use :meth:`from_item` and :meth:`to_item` to create and restore.
    """
    record_type: Literal['snapshot'] = 'snapshot'
    item: EntityT
    item_state_hash: Hash

    @classmethod
    def from_item(cls, item: EntityT) -> Snapshot[EntityT]:
        return cls(item=deepcopy(item), item_state_hash=item._state_hash())

    def restore_item(self) -> EntityT:
        return deepcopy(self.item)
