from uuid import UUID
from typing import TypeVar, Generic, Iterable
import logging
from dataclasses import dataclass, field

from .entity import Entity

logger = logging.getLogger(__name__)

EntityT = TypeVar("EntityT", bound=Entity)

@dataclass
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
            return self.data.get(criteria["uid"])
        return next((o for o in self.data.values() if o.matches(**criteria)), None)

    def find_all(self, **criteria) -> Iterable[EntityT]:
        # robust search: UID, label, tags
        if "uid" in criteria:
            return [ self.data.get(criteria["uid"]) ]
        return (o for o in self.data.values() if o.matches(**criteria))
