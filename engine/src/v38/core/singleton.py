# tangl/core/singleton.py
from __future__ import annotations
from typing import ClassVar, Self, Optional
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
    - No order optimization for creation, so use cautiously and ensure items aren't referenced until _after_ they've been created.

    Example:
        >>> class S(InstanceInheritance): value: str = Field()
        >>> S(label="foo", value="bar").value
        'bar'
        >>> S(label="baz", inherit_from="foo").value
        'bar'
        >>> S(label="foobar", inherit_from="baz").value
        'bar'
    """
    inherit_from: Optional[str] = Field(None, init_var=True)

    def __init__(self, *, label: str, inherit_from: str = None, **kwargs):
        if inherit_from is not None:
            # Copy defaults from reference, discard identity fields (label, uid)
            # and inherit_from
            field_names = [ f for f in self.__pydantic_fields__.keys()
                            if f not in ['uid', 'inherit_from', 'label', *kwargs.keys()]
                            and not f.startswith('_') ]
            inherit_inst = self.get_instance(inherit_from)
            if inherit_inst is None:
                raise ValueError(f"'{inherit_from}' is not a valid heritage")
            defaults = {f: getattr(inherit_inst, f) for f in field_names}
            kwargs = defaults | kwargs

        super().__init__(label=label, inherit_from=inherit_from, **kwargs)

