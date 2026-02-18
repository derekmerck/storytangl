from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core38 import Entity, Graph, Record, Registry

class OpEnum(Enum):
    CREATE = "create"
    READ = "read"  # Unwatched
    UPDATE = "update"
    DELETE = "delete"


class Event(Record):

    operation: OpEnum

    item_id: UUID | None = None          # entity.uid
    field: str | None = None             # entity.locals
    key: str | int | UUID | None = None  # entity.locals[foo] or registry.get(key)
    value: Any = None             # entity.locals[foo] = bar or registry.add(value)

    prior_value: Any = None

    def apply(self, registry: Registry) -> None:
        if not isinstance(registry, Registry):
            raise ValueError(f"Invalid registry type {type(registry)} for patch")
        item_id = self.item_id

        # MVP replay uses entity-level CRUD deltas.
        if self.operation == OpEnum.CREATE:
            value = self.value
            if isinstance(value, dict):
                value = Entity.structure(value)
            if not isinstance(value, Entity):
                raise ValueError("CREATE event requires entity payload")
            if item_id is not None and value.uid != item_id:
                raise ValueError("CREATE event item_id does not match payload uid")
            registry.add(value)
            return

        if self.operation == OpEnum.DELETE and item_id is not None and self.field is None:
            registry.remove(item_id)
            return

        if self.operation == OpEnum.UPDATE and item_id is not None and self.field is None:
            value = self.value
            if isinstance(value, dict):
                value = Entity.structure(value)
            if not isinstance(value, Entity):
                raise ValueError("UPDATE event requires entity payload")
            if value.uid != item_id:
                raise ValueError("UPDATE event item_id does not match payload uid")
            # overwrite by uid while preserving key order
            registry.add(value)
            return

        # Backward-compatible narrow field update path.
        if item_id is None:
            raise ValueError(f"Invalid event {self!r}: missing item_id")
        item = registry.get(item_id)
        if item is None:
            raise ValueError(f"Invalid event {self!r}: target item not found")
        if self.key is None and self.field is not None:
            if self.operation == OpEnum.UPDATE:
                setattr(item, self.field, self.value)
                return
            if self.operation == OpEnum.DELETE:
                delattr(item, self.field)
                return
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

    def apply(self, registry: Registry) -> Registry:
        self._validate_registry_pre(registry)
        for event in self.events:
            event.apply(registry)
        self._validate_registry_post(registry)
        return registry

    def apply_to(self, graph: Graph) -> Graph:
        """Protocol hook used by replay engines."""
        self.apply(graph)
        return graph
