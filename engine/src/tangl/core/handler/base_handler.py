from __future__ import annotations
from typing import Callable, Any, Generic, TypeVar, Optional, Type, Self
import logging
import functools

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.core.entity import Entity
from tangl.core.entity.entity import EntityP
from .enums import HandlerPriority

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BaseHandlerP(EntityP):
    func: Callable[[Entity, StringMap], Any]
    priority: int = HandlerPriority.DEFAULT
    caller_criteria: StringMap
    owner_cls: Optional[Type[Entity]]  # class that defines this handler

@functools.total_ordering
class BaseHandler(Entity, Generic[T]):
    func: Callable[[Entity, StringMap], T]  # Return type is determined by handler kind
    priority: int | HandlerPriority = HandlerPriority.DEFAULT

    caller_criteria: StringMap = Field(default_factory=dict)
    owner_cls_: Optional[Type[Entity]] = Field(None, alias="owner_cls")

    @property
    def owner_cls(self) -> Optional[Type[Entity]]:
        if self.owner_cls_ is None:
            self.owner_cls_ = self._infer_owner_cls()
        logger.debug(f"h:{self.func.__name__}.owner_cls={self.owner_cls_}")
        return self.owner_cls_

    # terminology here is a little off, this is the an inv func relative to has_cls
    def has_owner_cls(self, entity: Entity) -> bool:
        logger.debug(f"h:Comparing owner_cls to caller_cls={entity.__class__}")
        if self.owner_cls is None:
            logger.debug(f"h:owner_cls is None, so always true")
            return True
        return isinstance(entity, self.owner_cls)

    def _infer_owner_cls(self):
        """
        Lazily determine the actual class that owns this handler
        if it was not explicitly specified at creation time.

        Instance methods, for example, can be inferred by parsing
        ``func.__qualname__`` to get the immediate parent class name,
        then dereferencing that name in the Tangl entity hierarchy.

        :return: The class object representing the method's owner, or None
                 if it's a staticmethod/lambda.
        :rtype: Optional[Type[Entity]]
        """
        if not isinstance(self.func, (classmethod, staticmethod)) and not self.func.__name__ == "<lambda>":
            parts = self.func.__qualname__.split('.')
            if len(parts) < 2:
                # raise ValueError("Cannot get outer scope name for module-level func")
                return None
            possible_class_name = parts[-2]  # the thing before .method_name
            logger.debug(f'Parsing owner class as {possible_class_name}')
            try:
                owner_cls = dereference_obj_cls(Entity, possible_class_name)
                logger.debug(f'Found {owner_cls}')
                return owner_cls
            except ValueError:
                logger.debug(f'Failed to dereference owner class')
                # return None if we can't evaluate it
                return None

    def has_func_name(self, value: str) -> bool:
        return self.func.__name__ == value

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
