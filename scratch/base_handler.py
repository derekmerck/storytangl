from __future__ import annotations
from typing import Generic, Union, Type, Self, runtime_checkable, Protocol, Any, Optional, TypeVar

import logging
import functools

from pydantic import Field, field_validator, BaseModel, ValidationInfo

from tangl.type_hints import StringMap, Primitive
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.core.entity import Entity
from tangl.core.entity.entity import match_logger
from .enums import HandlerPriority

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Union[Entity, Primitive])

@runtime_checkable
class HandlerFunc(Protocol[T]):
    def __call__(
        self,
        entity: Entity,
        ctx: dict,
        *,
        caller: Optional[Entity] = None,
        other: Optional[Entity] = None,
        result: Optional[Any] = None,
    ) -> T: ...

class HandlerResult(BaseModel):
    result: Any
    status: str
    errors: list
    handler: BaseHandler

PipelineResult = list[HandlerResult]

"""
Registration pattern:

decorator: handler
- creates a handler wrapper and attaches it to the function
- may not know caller class for predicate, looks for "other", "result", and "caller" in sig

registration:
on init subclass - check all class funcs and look for handler objects to register

"""

@functools.total_ordering
class BaseHandler(Entity, Generic[T], arbitrary_types_allowed=True):
    func: HandlerFunc[T]  # Return type is determined by handler kind

    service_name: Optional[str] = None
    priority: int | HandlerPriority = HandlerPriority.DEFAULT

    takes_caller: bool = False
    # some instance handlers are defined on an owner that is not the caller
    takes_other: bool = False
    # some handlers can compare or mediate between two entities
    takes_result: bool = True
    # some handlers are 'pipeline ready'

    caller_cls: Type[Entity] = Entity
    caller_criteria: StringMap = Field(default_factory=dict)

    promiscuous: bool = False  # ignore owner-class, include "caller" field in kwargs
    owner: Optional[Entity] = None
    owner_cls_: Optional[Type[Entity]] = Field(None, alias="owner_cls")

    @field_validator("owner", mode="after")
    @classmethod
    def _confirm_owner_if_promiscuous(cls, value, info: ValidationInfo) -> None:
        if info.data.get("promiscuous") and value is None:
            raise ValueError("Promiscuous bindings require a declared owner")

    @field_validator('caller_criteria', mode="before")
    def _convert_none_to_empty_dict(cls, data):
        if data is None:
            data = {}
        return data

    @property
    def owner_cls(self) -> Optional[Type[Entity]]:
        # If it's explicitly set to None, ignore it
        if self.owner_cls_ is None and "owner_cls_" not in self.model_fields_set:
            self.owner_cls_ = self._infer_owner_cls()
        match_logger.debug(f"h:{self.func.__name__}.owner_cls={self.owner_cls_}")
        return self.owner_cls_

    @owner_cls.setter
    def owner_cls(self, value: Type[Entity]):
        self.owner_cls_ = value

    # terminology here is a little off, this is the inv func relative to has_cls
    def has_owner_cls(self, entity: Entity) -> bool:
        match_logger.debug(f"h:Comparing owner_cls to caller_cls={entity.__class__}")
        if self.owner_cls is None:
            match_logger.debug(f"h:owner_cls is None, so always true")
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

    @property
    def label(self):
        # default label is func name
        return self.label_ or self.func.__name__

    # For matching
    def has_func_name(self, value: str) -> bool:
        return self.func.__name__ == value

    is_instance_handler: bool = False     # Instance handlers sort before class handlers
    registration_order: int = -1

    def __call__(self, entity: Entity, context: StringMap, caller: Entity = None) -> T:
        if self.promiscuous:
            # bind owner to 'self' and inject the caller as a kwarg
            return self.func(self.owner, context, caller=entity)
        # it's an inherited function
        return self.func(entity, context)

    def sort_key(self, caller: Entity = None):

        # Cannot infer relative mro distance without a reference caller
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
