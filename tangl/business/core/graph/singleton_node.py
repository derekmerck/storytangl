from __future__ import annotations
from typing import TypeVar, Generic, ClassVar, Type, Self, Any
import sys
import logging

import pydantic
from pydantic import Field, field_validator

from tangl.type_hints import UniqueLabel
from tangl.business.core import Singleton
# noinspection PyUnresolvedReferences
from .graph import Node, Graph

logger = logging.getLogger(__name__)

WrappedType = TypeVar("WrappedType", bound=Singleton)

class SingletonNode(Node, Generic[WrappedType]):
    # Allows embedding a singleton into a mutable node so its properties can be
    # referenced indirectly via a graph
    # Note that singletons are frozen, so you shouldn't mess with its referred attributes.

    #: The singleton entity class that this wrapper is associated with.
    wrapped_cls: ClassVar[Type[Singleton]] = None

    label: UniqueLabel = Field(...)  # required

    # noinspection PyNestedDecorators
    @field_validator("label")
    @classmethod
    def _valid_label_for_wrapped_cls(cls, value: str) -> str:
        if not cls.wrapped_cls.get_instance(value):
            raise ValueError(f"No instance of `{cls.wrapped_cls.__name__}` found for ref label `{value}`.")
        return value

    @property
    def reference_singleton(self) -> WrappedType:
        res = self.wrapped_cls.get_instance(self.label)
        if not res:
            raise ValueError(f"No instance of `{self.wrapped_cls.__name__}` found for ref label `{self.label}`.")
        return self.wrapped_cls.get_instance(self.label)

    def __getattr__(self, name: str) -> Any:
        if hasattr(self.reference_singleton, name):
            return getattr(self.reference_singleton, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @classmethod
    def _instance_vars(cls, wrapped_cls: Type[WrappedType] = None):
        wrapped_cls = wrapped_cls or cls.get_wrapped_cls()
        return {k: (v.annotation, v) for k, v in wrapped_cls.__pydantic_fields__.items()
                if v.json_schema_extra and v.json_schema_extra.get("instance_var")}

    @classmethod
    def _create_wrapper_cls(cls, wrapped_cls: Type[WrappedType], name: str = None) -> Type[Self]:
        """Class method to dynamically create a new wrapper class given a reference singleton type."""
        name = name or f"{cls.__name__}[{wrapped_cls.__name__}]"
        module = sys.modules[__name__]

        if new_cls := getattr(module, name, None):
            logger.debug(f"Found extant wrapper class {new_cls.__name__}")
            return new_cls

        instance_vars = cls._instance_vars(wrapped_cls)
        generic_metadata = {'origin': cls, 'args': (wrapped_cls,), 'parameters': ()}

        new_cls = pydantic.create_model(name,
                                        __base__= cls,
                                        __pydantic_generic_metadata__=generic_metadata,
                                        wrapped_cls = wrapped_cls,
                                        **instance_vars )

        # Adding the ephemeral class to this module's namespace allows them to be pickled and cached
        setattr(module, name, new_cls)

        return new_cls

    @classmethod
    def __class_getitem__(cls, wrapped_cls: Type[WrappedType]) -> Type[Self]:
        """
        Unfortunately difficult to use pydantic's native Generic handling with this b/c we
        want to manipulate the fields as the model is created.
        """
        return cls._create_wrapper_cls(wrapped_cls)
