from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core38 import Record, Registry

class OpEnum(Enum):
    CREATE = "create"
    READ = "read"  # Unwatched
    UPDATE = "update"
    DELETE = "delete"


class Event(Record):

    operation: OpEnum

    item_id: UUID = None          # entity.uid
    field: str = None             # entity.locals
    key: str | int | UUID = None  # entity.locals[foo] or registry.get(key)
    value: Any = None             # entity.locals[foo] = bar or registry.add(value)

    prior_value: Any = None

    def apply(self, registry: Registry) -> None:
        if not isinstance(registry, Registry):
            raise ValueError(f"Invalid registry type {type(registry)} for patch")
        # should also check called on an unwatched registry

        if self.item_id == registry.uid:
            item = registry
        else:
            item = registry.get(self.item_id)

        # member manipulation
        if item is registry and self.field is None:
            match self.operation:
                case OpEnum.CREATE:
                    # adding item to registry
                    # key should be None, value is an entity
                    registry.add(self.value)
                case OpEnum.DELETE:
                    # deleting an item from registry
                    # key should be UUID, value should be None
                    registry.remove(self.key)
                case _:
                    # registry UPDATE without a field is invalid, READ is irrelevant
                    raise ValueError(f"Invalid member event {self!r} for registry {registry!r}.")
            return

        # unkeyed field manipulation
        if self.key is None:
            # unkeyed field manipulation
            match self.operation:
                case OpEnum.UPDATE:
                    setattr(item, self.field, self.value)
                case OpEnum.DELETE:
                    # seems unlikely to be used
                    delattr(item, self.field)
                case _:
                    # item CREATE is always an UPDATE, READ is irrelevant
                    raise ValueError(f"Invalid event {self!r} for entity.")
            return

        # general case: item.field[key0.key1.key2] = value
        ...

        raise ValueError(f"Invalid event {self!r} for item {item!r}.")


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
