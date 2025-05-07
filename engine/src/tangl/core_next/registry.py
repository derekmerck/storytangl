from uuid import UUID
from typing import TypeVar, Generic, Iterable
from collections import defaultdict
import logging

from pydantic import Field

from .requirement import ProvisionKey, Providable
from .entity import Entity

logger = logging.getLogger(__name__)

EntityT = TypeVar("EntityT", bound=Entity)

class Registry(Entity, Generic[EntityT]):
    registry: dict[UUID, EntityT] = Field(default_factory=dict, repr=False)
    index: dict[ProvisionKey, set[UUID]] = Field(default_factory=lambda: defaultdict(set), repr=False)

    # -------- public API ----------
    def add(self, obj: Entity):
        if not hasattr(obj, "uid"):
            raise ValueError(f"Cannot register objects without a uid {type(obj)}")
        self.registry[obj.uid] = obj
        if isinstance(obj, Providable):
            logger.debug(f"adding {obj!r} to {obj.provides}")
            for key in obj.provides:
                logger.debug(f"->adding {obj!r} to {key!r}")
                self.index[key].add(obj.uid)

    def add_all(self, *objs: Entity):
        for obj in objs:
            self.add(obj)

    def find_one(self, **criteria):
        # robust search: UID, label, tags, or ProvisionKey
        logger.debug(f"searching for {criteria}")
        if "uid" in criteria:
            return self.registry.get(criteria["uid"])
        if "provides" in criteria:
            logger.debug(f"searching for {criteria['provides']!r} provider")
            providers = self.index.get(criteria["provides"])
            logger.debug(f"found {providers} id's")
            if providers:
                return self.registry[next(iter(providers))]
        return next((o for o in self.registry.values() if o.matches(**criteria)), None)

    def find_all(self, **criteria) -> Iterable[Entity]:
        # robust search: UID, label, tags, or ProvisionKey
        if "uid" in criteria:
            return [ self.registry.get(criteria["uid"]) ]
        if "provides" in criteria:
            providers = self.index.get(criteria["provides"], [])
            return [ self.registry[p] for p in providers ]
        return (o for o in self.registry.values() if o.matches(**criteria))
