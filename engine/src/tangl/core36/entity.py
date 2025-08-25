from __future__ import annotations
from uuid import UUID
from typing import Any, TypeVar, Generic, Self, Iterator, ClassVar
from dataclasses import dataclass, field, asdict

from tangl.type_hints import Label, Tag, UnstructuredData

@dataclass
class Entity:
    uid: UUID = field(default_factory=UUID)
    label: Label = None
    tags: set[Tag] = field(default_factory=set)

    def matches(self, **criteria) -> bool:
        for k, v in criteria.items():
            if getattr(self, k, None) != v:
                return False
        return True

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        cls_ = data.pop('obj_cls', cls)
        return cls_(**data)

    def unstructure(self) -> UnstructuredData:
        data = asdict(self)  # todo: skip hidden/private/shared like shape registry unless explicit
        data["obj_cls"] = self.__class__
        return data

RT = TypeVar("RT", bound=Entity)
@dataclass
class Registry(dict[UUID, RT], Generic[RT]):
    data: dict[UUID, Entity] = field(default_factory=dict)

    def get(self, uid: UUID) -> RT:
        return self.data.get(uid)

    def find(self, **criteria: Any) -> Iterator[RT]:
        return filter(lambda x: x.matches(**criteria), self.data)

    def add(self, entity: RT):
        if entity.uid in self.data:
            raise ValueError(f"Entity {entity} already registered")
        self.data[entity.uid] = entity

    def remove(self, entity: RT | UUID):
        if isinstance(entity, UUID):
            el_id = entity
        elif isinstance(entity, Entity):
            el_id = entity.uid
        else:
            raise TypeError("Expected UUID or Entity")
        self.data.pop(el_id, None)

    def __contains__(self, item: UUID | RT) -> bool:
        if isinstance(item, UUID):
            return item in self.data
        elif isinstance(item, Entity):
            return item.uid in self.data
        elif isinstance(item, Label):
            return item in self.all_labels()
        raise TypeError("Expected UUID or Entity")

    def all_labels(self) -> list[str]:
        return [ v.label for v in self.data.values() if v.label is not None ]

    def all_tags(self) -> set[str]:
        tags = set()
        for v in self.data.values():
            tags.update(v.tags)
        return tags

class SingletonEntity(Entity):
    _instances: ClassVar[Registry[Self]] = Registry()

    def __init__(self, *args, **kwargs) -> None:
        label = kwargs.get("label")
        if not label:
            raise RuntimeError(f"{self.__class__.__name__} must have label")
        elif label in self._instances:
            raise RuntimeError(f"{self.__class__.__name__} already has {label}, use `get_instance` instead")
        super().__init__(*args, **kwargs)
        self._instances[self.uid] = self

    @classmethod
    def get_instance(cls, label: str) -> Self:
        return next(cls._instances.find(label=label), None)

    # Unstructure by name

    def unstructure(self) -> UnstructuredData:
        return {'obj_cls': self.__class__, 'label': self.label}

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        return cls.get_instance(label=data.get('label'))
