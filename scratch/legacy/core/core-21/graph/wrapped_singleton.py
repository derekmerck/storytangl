import functools
from typing import ClassVar, Type, Callable
import logging
import sys

import pydantic
from pydantic import BaseModel

from tangl.type_hints import UniqueLabel
from tangl.core.singleton import Singleton
from tangl.entity.smart_new import SmartNewHandler
from tangl.core.graph import Node, NodeType

logger = logging.getLogger("tangl.graph.wrapped")
logger.setLevel(logging.WARNING)

class WrappedSingleton(BaseModel):
    """
    A mixin class that wraps a singleton entity with instance-specific state and enables it to be attached to a graph as a Node.

    This class allows for individual instances to have unique states while sharing common properties and methods defined in the singleton entity.

    Attributes on the reference entity are passed through the wrapper.  Local copies are created for attributes marked  "instance_var" in the schema and class methods `method(cls, inst)` are rebound to the wrapped instance.

    Create a wrapped class:

    > Token = WrappedSingleton.create_wrapper_class("Token", Singleton)

    Attributes:
        label (UniqueLabel): The unique identifier for the specific singleton entity instance.
        wrapped_cls (ClassVar[Type[SingletonEntity]]): The singleton entity class that this wrapper is associated with.

    Methods:
        __init__(self, reference_entity_id, **kwargs): Initializes a new instance of the wrapper.
        __getattr__(self, item): Delegates attribute access to the singleton entity.
        create_wrapper_cls(cls, name, reference_entity_cls): Class method to dynamically create a new wrapper class given a reference singleton entity.
    """
    wrapped_cls: ClassVar[Type[SingletonEntity]] = SingletonEntity

    @SmartNewHandler.handle_kwargs_strategy
    def _create_reference_entity_if_missing(cls, label: UniqueLabel = None, **kwargs: dict):
        # create ref entity and throw out non-instance kwargs
        logger.debug("running create_ref in wrapped singleton")

        if not label:
            raise RuntimeError(f"Wrapped singletons must use the `label` field to refer to their referent {kwargs}")

        if label not in cls.wrapped_cls._instances:
            cls.wrapped_cls(label=label, **kwargs)

        instance_kwargs = { k: v for k, v in kwargs.items() if k in cls.instance_vars()}
        return {'label': label,
                **instance_kwargs}

    def __init__(self, label: UniqueLabel | wrapped_cls,
                 from_ref = None,
                 tags = None,
                 **kwargs):

        # dereference the from_ref's label if passed as inst
        if isinstance(label, self.wrapped_cls):
            label = label.label

        # create a reference instance if one doesn't already exist
        if label not in self.wrapped_cls._instances:
            self.wrapped_cls(label=label, from_ref=from_ref, tags=tags, **kwargs)
            kwargs = { k: v for k, v in kwargs.items() if k in self.instance_vars(self.wrapped_cls)}

        super().__init__(label=label, **kwargs)

        # Union with the reference entity's tags
        self.tags |= self.reference_entity.tags

    @property
    def reference_entity(self) -> SingletonEntity:
        return self.wrapped_cls.get_instance(self.label)

    def __getattr__(self, item):
        # Delegate attribute access to the reference entity
        if hasattr(self.reference_entity, item):
            # print( item )
            attr = getattr(self.reference_entity, item)
            if callable(attr):
                # If it's a method, bind it to the reference_entity
                # This only works with cls methods that take 'self' as the 2nd param, see Wearable
                return functools.partial(attr, self)
            return attr
        return super().__getattr__(item)

        # raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    @classmethod
    def instance_vars(cls, wrapped_cls: Type[SingletonEntity] = None):
        wrapped_cls = wrapped_cls or cls.wrapped_cls
        return {k: (v.annotation, v) for k, v in wrapped_cls.model_fields.items()
                if v.json_schema_extra and v.json_schema_extra.get("instance_var")}

    @classmethod
    def singleton_vars(cls, wrapped_cls: Type[SingletonEntity] = None):
        wrapped_cls = wrapped_cls or cls.wrapped_cls
        return {k: (v.annotation, v) for k, v in wrapped_cls.model_fields.items()
                if not v.json_schema_extra or not v.json_schema_extra.get("instance_var")}

    @classmethod
    def create_wrapper_cls(cls, name: str, wrapped_cls: Type[SingletonEntity]) -> Type[NodeType]:
        instance_vars = cls.instance_vars(wrapped_cls)
        new_cls = pydantic.create_model(name,
                                        __base__= (cls, Node),
                                        wrapped_cls = wrapped_cls,
                                        **instance_vars )

        # Adding the ephemeral class to this module's namespace allows them to be pickled
        module = sys.modules['tangl.graph.mixins.wrapped_singleton']
        setattr(module, name, new_cls)

        return new_cls

    def repr_data(self) -> dict:
        # print(f'wrapped repr {pydantic.BaseModel.model_dump(self.reference_entity, exclude_unset=True, exclude_defaults=True, exclude_none=True)}')
        data = super().repr_data()
        data |= pydantic.BaseModel.model_dump(self.reference_entity, exclude_unset=True, exclude_defaults=True, exclude_none=True, by_alias=True, exclude={'label'})
        return data