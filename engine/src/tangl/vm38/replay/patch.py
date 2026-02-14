from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core38 import Record, Registry, Entity

class OpEnum(Enum):
    CREATE = "create"
    READ = "read"  # Unwatched
    UPDATE = "update"
    DELETE = "delete"


class Event(Record):

    operation: OpEnum

    item_id: UUID = None          # entity
    field: str = None             # entity.locals
    key: str | int | UUID = None  # entity.locals[foo] or registry.get(key)
    value: Any = None             # entity.locals[foo] = bar or registry.add(value)

    prior_value: Any = None

    def apply(self, registry: Registry) -> None:

        match (self.operation,
               self.item_id is not None,   # entity ops have item id
               self.field is not None,     # entity ops have field name
               self.key is not None,       # registry ops and entity ops on collection fields have keys
               self.value is not None):    # any add or update has a value

            # should probably allow item_id to be registry.uid so we can get/set values
            #   other than members on it
            # so always an item id.
            # If it's the registry id:
            # - create with no field, key -> add(value)
            # - delete with no field -> remove(key)

            # Don't need handlers for:
            # - read reg item or entity field
            # - update reg item (which is always decomposed into item field updates)
            # - create field (never used)
            # - del field (never used)
            # todo: DO need to handle updating nested collections and setting sub-keyed values
            #       like item.locals['foo.bar'] = 'baz'

            # registry ops, no keys
            # ---------------------
            case OpEnum.CREATE, False, False, False, True:
                # adding item to registry
                registry.add(self.value)

            case OpEnum.DELETE, True, False, False:
                # deleting an item from registry
                registry.remove(self.item_id)

            # item ops, have item_id, key
            # ---------------------------
            case OpEnum.UPDATE, True, True, True:
                # if we are tracking prior value, we can incrementally confirm it before updating.
                item = registry.get(self.item_id)
                setattr(item, self.key, self.value)

            case _:
                raise ValueError(f"Can't apply {self!r}!  Invalid operation or fields for op.")


class Patch(Record):

    registry_id: UUID
    initial_registry_value_hash: bytes
    final_registry_value_hash: bytes

    events: list[Event] = Field(default_factory=list)
    # patch event chains can definitely be canonicalized, reduced by removing
    # updates followed by deletes, and condensed into single multi-field/key
    # updates for an item, but that is an optimization concern.

    def _validate_registry_pre(self, registry: Registry) -> bool:
        if self.registry_id != registry.uid:
            raise ValueError("Invalid registry for patch")
        if self.initial_registry_value_hash != registry.value_hash():
            raise ValueError("Invalid initial registry state for patch")
        return True

    def _validate_registry_post(self, registry: Registry) -> bool:
        if self.final_registry_value_hash != registry.value_hash():
            raise ValueError("Patch failed!  Invalid final registry state for patch")
        return True

    def apply(self, registry: Registry) -> None:
        self._validate_registry_pre(registry)
        for event in self.events:
            event.apply(registry)
        self._validate_registry_post(registry)
