from uuid import UUID
from typing import TypeVar, Generic, Iterable
from collections import defaultdict

from pydantic import Field

from .base import Entity, ProvisionKey, Providable

EntityT = TypeVar("EntityT", bound=Entity)

class Registry(Entity, Generic[EntityT]):
    registry: dict[UUID, EntityT] = Field(default_factory=dict, repr=False)
    index: dict[ProvisionKey, set[UUID]] = Field(default_factory=defaultdict[set], repr=False)

    # -------- public API ----------
    def add(self, obj: Entity):
        self.registry[obj.uid] = obj
        if isinstance(obj, Providable):
            for key in obj.provides:
                self.index[key] = obj.uid

    def add_all(self, *objs: Entity):
        for obj in objs:
            self.registry[obj.uid] = obj
            if isinstance(obj, Providable):
                for key in obj.provides:
                    self.index[key] = obj.uid

    def find_one(self, **criteria):
        # robust search: UID, label, tags, or ProvisionKey
        if "uid" in criteria:
            return self.registry.get(criteria["uid"])
        if "provides" in criteria:
            return self.registry.get(next(self.registry.get(criteria["provides"])))
        return next((o for o in self.registry.values() if o.matches(**criteria)), None)

    def find_all(self, **criteria) -> Iterable[Entity]:
        # robust search: UID, label, tags, or ProvisionKey
        if "uid" in criteria:
            return [ self.registry.get(criteria["uid"]) ]
        if "provides" in criteria:
            providers = self.index.get(criteria["provides"], [])
            return [ self.registry[p] for p in providers ]
        return (o for o in self.registry.values() if o.matches(**criteria))
