from __future__ import annotations
from typing import TypeVar, Generic, Self, Optional
from uuid import UUID
import logging

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from tangl.type_hints import UniqueLabel, UnstructuredData
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from .entity import Entity

logger = logging.getLogger(__name__)

EntityT = TypeVar("EntityT", bound=Entity)

class Registry(dict[UUID, EntityT], Generic[EntityT]):

    def __setitem__(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__} is not setable by key, use `add(entity)`.")

    def __getitem__(self, key: UUID | UniqueLabel) -> EntityT:
        if isinstance(key, UniqueLabel):
            if x := self.find_one(label=key):
                return x
        return super().__getitem__(key)

    def add(self, value: EntityT, allow_overwrite: bool = False):
        if not allow_overwrite and value.uid in self:
            raise ValueError(f"Cannot overwrite {value.uid} in registry. Pass `allow_overwrite=True` to force overwrite.")
        super().__setitem__(value.uid, value)

    def remove(self, value: EntityT):
        # this is actually more like discard since it doesn't fail if the key is missing
        self.pop(value.uid, None)

    def find(self, **criteria) -> list[EntityT]:
        return Entity.filter_by_criteria(self.values(), **criteria)

    def find_one(self, **criteria) -> Optional[EntityT]:
        return Entity.filter_by_criteria(self.values(), return_first=True, **criteria)

    def unstructure(self, *args, **kwargs) -> UnstructuredData:
        data = []
        for v in self.values():
            data.append(v.unstructure())
        return { 'obj_cls': self.__class__.__name__, 'data': data }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        this = obj_cls()
        data = data.pop('data', [])
        for v in data:
            item = Entity.structure(v)
            this.add(item)
        return this

    def __get_pydantic_core_schema__(self, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # this allows pydantic to create a complete schema for Node
        return core_schema.dict_schema(
            keys_schema=core_schema.uuid_schema(),
            values_schema=handler.generate_schema(EntityT)
        )
