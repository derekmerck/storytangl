from __future__ import annotations
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from tangl.type_hints import Identifier, HasUid

class IndirectMapping(BaseModel):
    # Optional wrapper for the storage manager to support a key-map

    keys: dict[Identifier, UUID] = Field(default_factory=dict)
    data: dict[UUID, HasUid] = Field(default_factory=dict)

    def add_key(self, key: Identifier, item_id: UUID):
        self.clear_keys_for(item_id)
        self.keys[key] = item_id

    def clear_keys_for(self, item_id: UUID):
        current_keys = [k for k, v in self.keys.items() if v == item_id]
        for k in current_keys:
            del self.keys[k]

    def __delitem__(self, key: Identifier):
        item_id = self.keys[key]
        del self.data[item_id]
        del self.keys[key]

    def __get_item__(self, key: Identifier) -> Any:
        item_id = self.keys.get(key)
        if item_id is None:
            raise KeyError(key)
        return self.data.get(item_id)

    def __set_item__(self, key: Identifier, item: Any):
        item_id = item.uid
        if key not in self.keys:
            self.add_key(key, item_id)
        self.data[item_id] = item
