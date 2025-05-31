from __future__ import annotations
from typing import Callable, Any, Generic, TypeVar, Optional, Type, Self
import logging
import functools

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.entity.entity import EntityP

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BaseHandlerP(EntityP):
    func: Callable[[Entity, StringMap], Any]
    priority: int = 0
    caller_criteria: StringMap
    owner_cls: Optional[Type[Entity]]  # class that defines this handler

@functools.total_ordering
class BaseHandler(Entity, Generic[T]):
    func: Callable[[Entity, StringMap], T]  # Return type is determined by handler kind
    priority: int = 0

    caller_criteria: StringMap = Field(default_factory=dict)
    owner_cls: Optional[Type[Entity]] = None

    is_instance_handler: bool = False     # Instance handlers sort before class handlers
    registration_order: int = -1

    def __call__(self, entity: Entity, context: StringMap) -> T:
        return self.func(entity, context)

    def sort_key(self, caller: Entity = None):

        if caller is None:
            return self.priority, not self.is_instance_handler, self.registration_order

        def mro_dist(sub_cls, super_cls):
            """Return MRO index: 0 for direct match, 1 for parent, etc. Large for unrelated."""
            try:
                return sub_cls.__class__.mro().index(super_cls)
            except ValueError:
                return 999  # Arbitrarily large if not in hierarchy

        return (self.priority,
                not self.is_instance_handler,
                mro_dist(caller, self.owner_cls),
                self.registration_order)

    def __lt__(self, other: Self):
        return self.sort_key() < other.sort_key()
