from __future__ import annotations
from typing import Self

from pydantic import Field
from wrapt import ObjectProxy

from tangl.core38 import on_get_item, Registry, Entity
from .observer import RegistryObserver
from .patch import Event

# Not sure simplest way to do this.
# - could use dispatch hook for registry events
# - need wrapper for field events
# - maybe best to just be consistent and use wrapper for both

class WraptCollection: ...

class WraptEntity(ObjectProxy):
    @classmethod
    def from_item(cls, item: Entity) -> Self:
        ...

class WraptRegistry(ObjectProxy):
    registry: Registry
    observers: list[RegistryObserver] = Field(default_factory=list)

    def submit_event(self, event: Event):
        for observer in self.observers:
            observer.submit_event(event)

@on_get_item
def _return_a_proxy(registry, item_id, _ctx=None) -> WraptEntity:
    return WraptEntity.from_item(registry.get(item_id))
