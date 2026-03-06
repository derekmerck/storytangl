# tangl/core/singleton.py
"""Label-unique entities with per-class instance registries.

Singletons provide one instance per ``(class, label)`` within a process. They are
immutable concept-level references and serialize as lightweight references rather than
full entity payloads.

See Also
--------
:class:`tangl.core.registry.Registry`
    Internal storage for per-class singleton instance tables.
:mod:`tangl.core.token`
    Wrap singleton references into graph-native tokens when local runtime state is
    required.
"""

from __future__ import annotations

from copy import deepcopy
from importlib import resources
from inspect import isclass
from typing import ClassVar, Optional, Self
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator
import yaml

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
        """Allocate an isolated instance registry for each concrete subclass."""
        super().__init_subclass__(**kwargs)
        cls._instances = Registry()

    @classmethod
    def has_instance(cls, label: UUID | str) -> bool:
        """Return whether an instance with ``label`` is registered for this subclass."""
        if isinstance(label, UUID):
            return cls._instances.get(label) is not None
        return label in cls._instances.all_labels()

    @classmethod
    def get_instance(cls, label: UUID | str) -> Self | None:
        """Return the registered instance for ``label`` or ``uid`` when present."""
        if isinstance(label, UUID):
            return cls._instances.get(label)
        return cls._instances.find_one(label=label)

    @classmethod
    def find_instance(cls, **criteria) -> Self | None:
        """Legacy compatibility lookup by selector criteria."""
        return cls._instances.find_one(**criteria)

    @classmethod
    def find_all_instances(cls, **criteria):
        """Legacy compatibility iterator for selector-filtered instances."""
        return cls._instances.find_all(**criteria)

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all process-local instances for this subclass."""
        cls._instances.clear()

    @classmethod
    def all_instances(cls):
        """Legacy compatibility iterator over all registered instances."""
        return cls._instances.values()

    @classmethod
    def all_instance_labels(cls) -> list[str]:
        """Legacy compatibility helper returning labels for all instances."""
        return cls._instances.all_labels()

    @classmethod
    def load_instances(cls, data: dict) -> None:
        """Legacy compatibility helper for bulk singleton creation."""
        for label, kwargs in data.items():
            cls(label=label, **kwargs)

    @classmethod
    def load_instances_from_yaml(cls, resources_pkg: str, fn: str) -> None:
        """Legacy compatibility helper loading singleton instances from YAML."""
        payload = resources.files(resources_pkg).joinpath(fn).read_text()
        data = yaml.safe_load(payload) or {}
        cls.load_instances(data)

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
        """Return identity hash keyed by concrete class and label."""
        return hashing_func(self.__class__, self.label)

    def __hash__(self) -> int:
        return hash((self.__class__, self.label))

    def __reduce__(self):
        return self.__class__.get_instance, (self.label,)

    def unstructure(self) -> UnstructuredData:
        """Serialize singleton references by ``kind`` and ``label`` only."""
        return {"kind": self.__class__, "label": self.label}

    @classmethod
    def structure(cls, data) -> Self:
        """Resolve serialized singleton reference back to an existing live instance."""
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
                for field_name in type(self).model_fields.keys()
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


# Legacy compatibility alias retained during namespace cutover.
InheritingSingleton = InstanceInheritance
