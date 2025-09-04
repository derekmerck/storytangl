# tangl/core/registry.py
from typing import TypeVar, Generic, Optional, Iterator, overload, Self
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from .entity import Entity

VT = TypeVar("VT", bound=Entity)  # registry value type
FT = TypeVar("FT", bound=Entity)  # find type within registry

class Registry(Entity, Generic[VT]):
    data: dict[UUID, VT] = Field(default_factory=dict,
                                 json_schema_extra={'compare': False})

    def add(self, entity: VT):
        self.data[entity.uid] = entity

    def get(self, key: UUID) -> Optional[VT]:
        if isinstance(key, str):
            raise ValueError(
                f"Use find_one(label='{key}') instead of get('{key}') to get-by-label"
            )
        return self.data.get(key)

    def remove(self, key: VT | UUID):
        if isinstance(key, Entity):
            key = key.uid
        if not isinstance(key, UUID):
            raise ValueError(f"Wrong type for remove key {key}")
        self.data.pop(key)

    def keys(self) -> Iterator[UUID]:
        return iter(self.data.keys())

    def values(self) -> Iterator[VT]:
        return iter(self.data.values())

    def __bool__(self) -> bool:
        return bool(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def clear(self) -> None:
        self.data.clear()

    @overload
    def find_all(self, *, is_instance: FT, **criteria) -> Iterator[FT]:
        ...

    @overload
    def find_all(self, **criteria) -> Iterator[VT]:
        ...

    def find_all(self, **criteria):
        return Entity.filter_by_criteria(self.values(), **criteria)

    def find_one(self, **criteria) -> Optional[VT]:
        return next(self.find_all(**criteria), None)

    def __contains__(self, key: UUID | str | VT) -> bool:
        if isinstance(key, UUID):
            return key in self.data
        elif isinstance(key, Entity):
            return key in self.data.values()
        elif isinstance(key, str):
            return key in self.all_labels()
        raise ValueError(f"Unexpected key type for contains {type(key)}")

    def all_labels(self) -> list[str]:
        return [x.get_label() for x in self.data.values() if x.get_label() is not None]

    def all_tags(self) -> set[str]:
        tags = set()
        for x in self.data.values():
            tags.update(x.tags)
        return tags

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        _data = data.pop("_data", {})
        obj = super().structure(data)  # type: Self
        for v in _data:
            _obj = Entity.structure(v)
            obj.add(_obj)
        return obj

    def unstructure(self) -> StringMap:
        data = super().unstructure()
        data["_data"] = []
        for v in self.data.values():
            data['_data'].append(v.unstructure())
        return data
