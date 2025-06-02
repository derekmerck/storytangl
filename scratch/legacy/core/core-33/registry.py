"""
tangl.core.registry
===================

Collection management for entities with robust search capabilities.

The Registry provides a generic dictionary-like container for Entity
objects with enhanced retrieval options:

- UUID-based direct access for performance-critical operations
- Criteria-based flexible search for dynamic discovery
- Type safety via generic parameters
- Composition over inheritance for extensibility

The Registry underpins the core StoryTangl graph management.

This component is foundational as it enables decoupling between
storage patterns and retrieval logic, letting capabilities
find requirements and vice versa without direct references.
"""

from uuid import UUID
from typing import TypeVar, Generic, Iterable, Optional
import logging
from dataclasses import dataclass, field

from .entity import Entity

logger = logging.getLogger(__name__)

EntityT = TypeVar("EntityT", bound=Entity)

@dataclass(kw_only=True)
class Registry(dict, Generic[EntityT]):

    data: dict[UUID, EntityT] = field(default_factory=dict, repr=False)

    # -------- public API ----------
    def add(self, obj: EntityT):
        if not hasattr(obj, "uid"):
            raise ValueError(f"Cannot register objects without a uid {type(obj)}")
        self.data[obj.uid] = obj

    def add_all(self, *objs: EntityT):
        for obj in objs:
            self.add(obj)

    def find_one(self, **criteria) -> EntityT:
        # robust search: UID, label, tags, or ProvisionKey
        logger.debug(f"searching for {criteria}")
        if "uid" in criteria:
            return self.get(criteria["uid"])
        return next((o for o in self.data.values() if o.matches(**criteria)), None)

    def find_all(self, **criteria) -> Iterable[EntityT]:
        # robust search: UID, label, tags
        if "uid" in criteria:
            return [ self.get(criteria["uid"]) ]
        return (o for o in self.data.values() if o.matches(**criteria))

    def get(self, key: UUID) -> Optional[EntityT]:
        return self.data.get(key)

    def __getitem__(self, key: UUID) -> Optional[EntityT]:
        return self.data.get(key)

    def __contains__(self, key: UUID) -> bool:
        return key in self.data

    def keys(self):
        return list(self.data.keys())

    def __len__(self) -> int:
        return len(self.data)

    def __bool__(self):
        if len(self) > 0:
            return True
        return False
