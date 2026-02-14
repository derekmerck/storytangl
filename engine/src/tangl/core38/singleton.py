# tangl/core/singleton.py
"""Label-unique entities with per-class instance registries.

Singletons provide one instance per ``(class, label)`` within a process. They are
immutable concept-level references and serialize as lightweight references rather than
full entity payloads.

See Also
--------
:class:`tangl.core38.registry.Registry`
    Internal storage for per-class singleton instance tables.
:mod:`tangl.core38.token`
    Wrap singleton references into graph-native tokens when local runtime state is
    required.
"""

from __future__ import annotations

from copy import deepcopy
from inspect import isclass
from typing import ClassVar, Optional, Self

from pydantic import ConfigDict, Field, model_validator

from tangl.type_hints import UnstructuredData
from tangl.utils.hashing import hashing_func

from .bases import is_identifier
from .entity import Entity
from .registry import Registry
from .selector import Selector


class Singleton(Entity):
    """Process-local singleton keyed by ``label`` per concrete subclass.

    Why
    ---
    Singletons represent immutable concept-level references that should not be
    duplicated in-memory. They are identified by ``(class, label)`` rather than
    ``(class, uid)``.

    Key Features
    ------------
    - each subclass gets an isolated ``_instances`` registry via
      :meth:`__init_subclass__`;
    - duplicate labels are rejected before model construction;
    - un/structuring is reference-only (`kind` + `label`), resolving to existing
      instances.

    Notes
    -----
    - ``structure()`` expects the referenced instance to already exist.
    - use tokens when singleton concepts need graph-local mutable state.

    Example:
        >>> a = Singleton(label="abc"); _ = Singleton(label="def")
        >>> Singleton.has_instance("abc")
        True
        >>> Singleton.get_instance("abc") is a
        True
        >>> data = a.unstructure()
        >>> Singleton.structure(data) is a
        True
    """

    model_config = ConfigDict(frozen=True)

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
    def clear_instances(cls) -> None:
        cls._instances.clear()

    @model_validator(mode="before")
    @classmethod
    def _ensure_unique_label(cls, data):
        label = data.get("label")
        if label is None:
            raise ValueError("Singleton requires a non-None label")
        if cls.has_instance(label):
            raise ValueError(f"Singleton inst with label '{label}' already exists")
        return data

    def __init__(self, *, label: str, **kwargs):
        super().__init__(label=label, **kwargs)
        self._instances.add(self)

    @is_identifier
    def id_hash(self) -> bytes:
        return hashing_func(self.__class__, self.label)

    def __hash__(self) -> int:
        return hash((self.__class__, self.label))

    def __reduce__(self):
        return self.__class__.get_instance, (self.label,)

    def unstructure(self) -> UnstructuredData:
        return {"kind": self.__class__, "label": self.label}

    @classmethod
    def structure(cls, data) -> Self:
        cls_ = data.pop("kind", cls)
        if not isclass(cls_):
            raise TypeError(f"Expected {cls_} to be a class")
        label = data.pop("label")
        return cls_.get_instance(label)


class InstanceInheritance(Singleton):
    """Singleton with creation-time field inheritance from another instance.

    ``inherit_from`` copies non-identity, non-private fields from the referent at
    creation time only. Explicit kwargs override inherited values.

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
            field_names = [
                field_name
                for field_name in self.__pydantic_fields__.keys()
                if field_name not in ["uid", "inherit_from", "label", *kwargs.keys()]
                and not field_name.startswith("_")
            ]
            inherit_inst = self.get_instance(inherit_from)
            if inherit_inst is None:
                raise ValueError(f"'{inherit_from}' is not a valid heritage")
            defaults = {
                field_name: deepcopy(getattr(inherit_inst, field_name))
                for field_name in field_names
            }
            kwargs = defaults | kwargs

        super().__init__(label=label, inherit_from=inherit_from, **kwargs)
