from __future__ import annotations
from typing import ClassVar, Self, Generic, TypeVar
from inspect import isclass

from pydantic import model_validator, ValidationError, Field

from tangl.type_hints import UnstructuredData
from tangl.utils.hashing import hashing_func
from .bases import is_identifier
from .entity import Entity
from .registry import Registry
from .selector import Selector

class Singleton(Entity):
    """
    - Unique label within class namespace
    - unstrucctures as reference: (kind, {"label": ...})
    - singletons allow linking otherwise unstructurable entities
      carrying behaviors or other logic into a structurable group.
    - they may be linked directly, or wrapped with local state by
      a token-builder

    Example:
        >>> a = Singleton(label="abc"); b = Singleton(label="def")
        >>> try:
        ...     c = Singleton(label="abc")
        ... except ValidationError as e:
        ...     print(e)  # doctest: +ELLIPSIS
        1 validation error ...
        >>> Singleton.has_instance("abc")
        True
        >>> Singleton.has_instance("foo")
        False
        >>> Singleton.get_instance("abc") is a
        True
        >>> data = a.unstructure()
        >>> aa = Singleton.structure(data)
        >>> aa is a
        True
    """

    _instances: ClassVar[Registry[Self]] = Registry()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._instances = Registry()

    @classmethod
    def has_instance(cls, label: str) -> bool:
        return label in cls._instances.all_labels()

    @classmethod
    def get_instance(cls, label: str) -> Self:
        return cls._instances.find_one(Selector.from_identifier(label))

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()

    @model_validator(mode='before')
    @classmethod
    def _ensure_unique_label(cls, data):
        label = data.get('label')
        if label is None or cls.has_instance(label):
            raise ValueError(f"Singleton inst with label '{label}' already exists")
        return data

    def __init__(self, *, label: str, **kwargs):
        super().__init__(label=label, **kwargs)
        self._instances.add(self)

    @is_identifier
    def id_hash(self) -> bytes:
        # Id is by class and _label_ rather than class and uid.
        return hashing_func(self.__class__, self.label)

    def __reduce__(self):
        # pickles like it un/structures
        return self.__class__.get_instance, (self.label,)

    def unstructure(self) -> UnstructuredData:
        return {'kind': self.__class__, 'label': self.label}

    @classmethod
    def structure(cls, data) -> Self:
        cls_ = data.pop('kind', cls)
        if not isclass(cls_):
            raise TypeError(f"Expected {cls_} to be a class")
        label = data.pop('label')
        return cls_.get_instance(label)

class InstanceInheritance(Singleton):
    """
    - Optional init-only ref_id for inheritance chain
    - Default values collected at creation-time ONLY
    - No order optimization for creation, so use cautiously
    """
    ref_id: str = None

    def ref_inst(self):
        # irrelevant after creation, just for auditing
        return self.get_instance(self.ref_id)


ST = TypeVar("ST", bound=Singleton)

class SingletonToken(Entity, Generic[ST]):
    """
    class that masquerades as a Singleton template object with an overlay for local/dynamic vars and refers others to base class

    This is almost always going to be mixed with GraphItem and used by a graph to materialize and link a 'platonic' singleton as a concrete node.  Singleton type might be 'weapon' and inst might be 'sword'.  A sword token delegates methods and attributes to its reference singleton, but adds a local 'sharpness' variable.

    - Fields on the ref_kind annotated with 'local_field' will be added to the token on class creation and the field value on the ref_inst used for the default value on token construction
    - Other field references will be delegated to the ref directly.

    - No circular ref discovery is provided, use cautiously
    """
    ref_id: str = None

    def ref_kind(self):
        # helper to get generic type
        ...

    def ref_inst(self):
        return self.ref_kind().get_instance(self.ref_id)
