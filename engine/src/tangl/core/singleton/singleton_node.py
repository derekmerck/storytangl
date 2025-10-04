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
    SingletonNode(from_ref: UniqueStr)

    Graph node wrapper that attaches a :class:`~tangl.core.Singleton` to a graph with node-local state.

    Why
    ----
    Let immutable singletons participate in topology while allowing per-node state (e.g.,
    position, runtime flags) that does not mutate the singleton itself.

    Key Features
    ------------
    * **Binding** – :attr:`wrapped_cls` points to the singleton class; :attr:`label` selects instance.
    * **Delegation** – attribute access defers to the wrapped singleton; methods are rebound for convenience.
    * **Instance vars** – singleton fields marked ``json_schema_extra={"instance_var": True}``
      are materialized on the node for local override.
    * **Dynamic wrappers** – :meth:`__class_getitem__` / :meth:`_create_wrapper_cls` generate typed wrappers on demand.

    API
    ---
    - :attr:`wrapped_cls` – singleton type bound to this wrapper.
    - :attr:`label` – required label of the referenced instance; validated at creation.
    - :attr:`reference_singleton` – access the underlying instance.
    - :meth:`_instance_vars` – collect instance-var field definitions from the wrapped class.
    - :meth:`_create_wrapper_cls` – emit a new wrapper subclass with those fields.

    Notes
    -----
    Prefer modeling behavior in the singleton; keep node-local overrides minimal and explicit.
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
