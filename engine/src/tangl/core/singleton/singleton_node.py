# tangl/core/singleton/singleton_node.py
from __future__ import annotations
from types import MethodType
from typing import TypeVar, Generic, ClassVar, Type, Self, Any
import sys
import logging

import pydantic
from pydantic import Field, field_validator

from tangl.type_hints import UniqueLabel
from ..graph import Node, Graph
from .singleton import Singleton

logger = logging.getLogger(__name__)

WrappedType = TypeVar("WrappedType", bound=Singleton)

class SingletonNode(Node, Generic[WrappedType]):
    """
    SingletonNode is a :class:`~tangl.core.graph.Node` extension that wraps a
    :class:`~tangl.core.entity.Singleton` with instance-specific
    state, enabling it to be attached to a graph while maintaining singleton
    behavior.

    Key Features
    ------------
    * **Singleton Wrapper**: Wraps a Singleton, providing graph connectivity.  The wrapped Singleton is accessed via the :attr:`reference_entity` property.
    * **Instance Variables**: Supports instance-specific variables.  Instance variables must be marked with :code:`json_schema_extra={"instance_var": True}` in the Singleton.
    * **Method Rebinding**: Class methods are rebound to the wrapped instance.
    * **Dynamic Class Creation**: Provides a method :meth:`create_wrapper_cls` to create wrapper classes for specific Singleton types.
    * **Supports Generics**: SingletonNode[Singleton] automatically creates an appropriate class wrapper.

    Usage
    -----
    .. code-block:: python
        from tangl.core.graph import SingletonNode, Graph
        from tangl.core import Singleton

        class MyConstant(Singleton):
            value: int
            state: str = Field(default="initial", json_schema_extra={"instance_var": True})

        MyConstantNode = SingletonNode.create_wrapper_cls("MyConstantNode", MyConstant)

        graph = Graph()
        const_node1 = MyConstantNode(label="CONSTANT_1", value=42, graph=graph)
        const_node2 = MyConstantNode(label="CONSTANT_1", state="modified", graph=graph)

        print(const_node1.value == const_node2.value)  # True (42)
        print(const_node1.state != const_node2.state)  # True ("initial" != "modified")

    Related Components
    ------------------
    * :class:`~tangl.core.entity.Singleton`: The base class for singleton entities.
    * :class:`~tangl.core.graph.Node`: The base class for graph nodes.
    """
    # Allows embedding a Singleton into a mutable node so its properties can be
    # referenced indirectly via a graph
    # Note that singletons are frozen, so the referred attributes are immutable.

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
        """Delegates attribute access to non-instance-variables back to the reference singleton entity."""
        if hasattr(self.reference_singleton, name):
            attr = getattr(self.reference_singleton, name)
            if callable(attr):
                # If it's a method, bind it to the reference_entity
                # This only works with instance methods that take 'self' 1st param, see Wearable
                return MethodType(attr.__func__, self)
                # return functools.partial(attr, self)
            return attr
        raise AttributeError(f"{self.__class__.__name__} is missing attribute '{name}'")

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
        if isinstance(wrapped_cls, TypeVar):
            # Sometimes we want to use a type var
            wrapped_cls = wrapped_cls.__bound__
        return cls._create_wrapper_cls(wrapped_cls)
