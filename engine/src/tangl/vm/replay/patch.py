# tangl/vm/replay/patch.py
from typing import Optional, Literal, Iterable
from uuid import UUID

from pydantic import field_validator

from tangl.type_hints import Hash
from tangl.core import Record, Registry
from .events import Event

# todo: may want to use different patch formats:
#       - canonicalized events
#       - raw event sequence (for audit)
#       - dict-diff (update delta)

class Patch(Record):
    record_type: Literal['patch'] = 'patch'
    registry_id: Optional[UUID] = None
    registry_state_hash: Hash = None
    events: list[Event]

    @field_validator("events")
    @classmethod
    def _canonicalize_events(cls, data) -> Iterable[Event]:
        # may want to skip this, or just sort by seq
        return Event.canonicalize_events(data)

    def apply(self, registry: Registry) -> Registry:
        if self.registry_id and self.registry_id != registry.uid:
            raise ValueError(f"Wrong registry for patch {registry.uid} != {self.registry_id}")
        if self.registry_state_hash and self.registry_state_hash != registry._state_hash():
            raise ValueError(f"Wrong registry state hash for patch")

        return Event.apply_all(self.events, registry)

