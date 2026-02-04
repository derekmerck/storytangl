from __future__ import annotations
from typing import ClassVar, Self
from inspect import isclass

from pydantic import model_validator, ValidationError

from tangl.type_hints import UnstructuredData
from tangl.utils.hashing import hashing_func
from .bases import is_identifier
from .entity import Entity
from .registry import Registry
from .selector import Selector

class Singleton(Entity):
    """
    - instances require a unique label in the class space
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
    def has_instance(cls, label: str) -> bool:
        return label in cls._instances.all_labels()

    @classmethod
    def get_instance(cls, label: str) -> Self:
        return cls._instances.find_one(Selector.from_identifier(label))

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



# ST = TypeVar("ST", bound=Singleton)
#
# class SingletonWrapper(Entity, Generic[ST]):
#     # class that masquerades as a Singleton template object with an overlay for local/dynamic vars and refers others to base class
#     ...
