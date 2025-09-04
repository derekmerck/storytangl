# tangl/core/singleton.py
from __future__ import annotations
from typing import ClassVar, Self, Optional
from uuid import UUID

from pydantic import ConfigDict

from tangl.type_hints import UniqueLabel, StringMap
from tangl.utils.hasher import hashing_func
from tangl.core.entity import Entity
from tangl.core.registry import Registry

class Singleton(Entity):
    # can ignore uid in comparison, but label must be unique within class

    model_config = ConfigDict(frozen=True)

    label: UniqueLabel
    _instances: ClassVar[Registry[Self]] = Registry()

    def __init_subclass__(cls, **kwargs):
        cls._instances = Registry()  # keep an instance registry per subclass
        super().__init_subclass__()

    def __init__(self, *, label: str, **kwargs):
        if self.get_instance(label) is not None:
            raise ValueError(f"Singleton with label {label} already exists")
        super().__init__(label=label, **kwargs)
        self._instances.add(self)

    @classmethod
    def get_instance(cls, key: UUID | UniqueLabel) -> Optional[Self]:
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
        obj_cls, label = data['obj_cls'], data['label']
        return obj_cls.get_instance(label)

    def unstructure(self) -> StringMap:
        return {'obj_cls': self.__class__, 'label': self.label}

    def __reduce__(self) -> tuple:
        return self.__class__.get_instance, (self.label,)
