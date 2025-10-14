# tangl/core/singleton.py
from __future__ import annotations
from typing import ClassVar, Self, Optional, Iterator
from uuid import UUID

from pydantic import ConfigDict

from tangl.type_hints import UniqueLabel, StringMap
from tangl.utils.hashing import hashing_func
from tangl.core.entity import Entity
from tangl.core.registry import Registry

class Singleton(Entity):
    """
    Singleton(label: UniqueStr)

    Immutable, globally-registered entity identified by a unique label.

    Why
    ----
    Models concept- or resource-level constants (e.g., fabula primitives,
    media generators) that must have exactly one instance per label within a type.

    Key Features
    ------------
    * **Per-class registry** – instances are stored in a class-scoped :class:`Registry` for lookup.
    * **Label identity** – hashing/equality keyed by ``(class, label)``; ``uid`` ignored.
    * **Frozen** – Pydantic config is frozen; instances are immutable.
    * **Stable (de)serialization** – :meth:`structure` / :meth:`unstructure` by ``(class, label)`` to preserve identity.
    * **Pickle-friendly** – :meth:`__reduce__` resolves back to existing instance.

    API
    ---
    - :meth:`get_instance` / :meth:`find_instance(**criteria)<find_instance>` – lookup by UUID or label/criteria.
    - :meth:`all_instances` / :meth:`all_instance_labels` – iterate/inspect.
    - :meth:`clear_instances` – reset registry (tests, demos).
    - :meth:`structure` / :meth:`unstructure` – (de)serialization by label.

    See also
    --------
    :class:`~tangl.core.singleton.InheritingSingleton`
    :class:`~tangl.core.singleton.SingletonNode`
    """

    model_config = ConfigDict(frozen=True)

    label: UniqueLabel
    _instances: ClassVar[Registry[Self]] = Registry(label="singleton_instances")

    def __init_subclass__(cls, **kwargs):
        label = cls.__name__.lower() + "_instances"
        cls._instances = Registry(label=label)  # keep an instance registry per subclass
        super().__init_subclass__()

    def __init__(self, *, label: str, **kwargs):
        if self.get_instance(label) is not None:
            raise ValueError(f"Singleton with label {label} already exists")
        super().__init__(label=label, **kwargs)
        self._instances.add(self)

    @classmethod
    def get_instance(cls, key: UUID | UniqueLabel) -> Optional[Self]:
        # In this case, we will allow get by str and assume it's the label
        if isinstance(key, UUID):
            return cls._instances.get(key)
        elif isinstance(key, UniqueLabel):
            return cls.find_instance(label=key)
        raise ValueError(f"Unexpected key type for get instance {key}")

    @classmethod
    def find_instance(cls, **criteria) -> Optional[Self]:
        return cls._instances.find_one(**criteria)

    @classmethod
    def clear_instances(cls) -> None:
        cls._instances.clear()

    @classmethod
    def all_instances(cls) -> Iterator[Self]:
        return cls._instances.values()

    @classmethod
    def all_instance_labels(cls) -> list[str]:
        return cls._instances.all_labels()

    def _id_hash(self) -> bytes:
        # For persistent id's, either the uid or a field annotated as UniqueLabel
        return hashing_func(self.__class__, self.label)

    def __hash__(self) -> int:
        return hash((self.__class__, self.label))

    @classmethod
    def structure(cls, data: dict) -> Self:
        label = data.pop("label")
        # obj_cls may have already been popped off by Entity.structure()
        # and redirected here under proper cls
        obj_cls = data.get("obj_cls", cls)
        return obj_cls.get_instance(label)

    def unstructure(self) -> StringMap:
        return {'obj_cls': self.__class__, 'label': self.label}

    def __reduce__(self) -> tuple:
        return self.__class__.get_instance, (self.label,)
