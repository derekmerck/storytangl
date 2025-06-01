from typing import TypeVar, Generic, Optional, Iterator, Self, Callable
from uuid import UUID
import itertools

from pydantic import PrivateAttr

from tangl.type_hints import UnstructuredData, Tag
from .entity import Entity # has uid, label, tags

EntityT = TypeVar("EntityT", bound=Entity)

class RegistryP(Entity, Generic[EntityT]):
    def add(self, entity: EntityT): ...
    def remove(self, item: EntityT | UUID) -> None: ...
    def get(self, uid: UUID) -> Optional[EntityT]: ...
    def clear(self): ...
    def find_one(self, **criteria) -> Optional[EntityT]: ...
    def find_all(self, sort_key=None, **criteria) -> Iterator[EntityT]: ...
    def find_first(self, *, sort_key, **criteria) -> Optional[EntityT]: ...

    @classmethod
    def chain_find_all(cls, *registries: Self, sort_key = None, **criteria) -> Iterator[EntityT]: ...
    @classmethod
    def chain_find_first(cls, *registries: Self, sort_key, **criteria) -> Optional[EntityT]: ...

class Registry(Entity, Generic[EntityT]):

    _items: dict[UUID, EntityT] = PrivateAttr(default_factory=dict)

    # BASIC FEATURES

    def add(self, item: EntityT) -> None:
        self._items[item.uid] = item

    def remove(self, item: EntityT | UUID) -> None:
        if not isinstance(item, UUID):
            item = getattr(item, "uid", None)
        self._items.pop(item, None)

    def get(self, uid: UUID) -> Optional[EntityT]:
        return self._items.get(uid)

    def __getitem__(self, uid: UUID) -> EntityT:
        return self._items[uid]

    def clear(self):
        self._items.clear()

    def find_one(self, sort_key=None, **criteria) -> Optional[EntityT]:
        if sort_key is None:
            return next((item for item in self if item.matches(**criteria)), None)
        else:
            return min(self.find_all(**criteria), key=sort_key)

    def find_first(self, *, sort_key, **criteria) -> Optional[EntityT]:
        return self.find_one(sort_key=sort_key, **criteria)

    def find_all(self, sort_key=None, filt: Callable[[EntityT], bool] = None, **criteria) -> Iterator[EntityT]:
        # todo: filt is only implemented here for now b/c changing the entire interface is a pain
        filt = filt or (lambda x: True)
        if sort_key is None:
            yield from (item for item in self if item.matches(**criteria) and filt(item))
        else:
            yield from (item for item in sorted(self, key=sort_key) if item.matches(**criteria) and filt(item))

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def __iter__(self) -> Iterator[EntityT]:
        return iter(self._items.values())

    def __contains__(self, item: UUID | EntityT) -> bool:
        if isinstance(item, UUID):
            return item in self._items
        elif isinstance(item, Entity):
            return item in self.all()
        raise TypeError(f"'{item}' is not an instance of UUID or Entity")

    # CHAINED FIND

    @classmethod
    def chain_find_all(cls, *registries: Self, sort_key = None, **criteria) -> Iterator[EntityT]:
        reg_iter = itertools.chain.from_iterable(registry.find_all(**criteria) for registry in registries)
        if sort_key is None:
            yield from reg_iter
        else:
            yield from sorted(reg_iter, key=sort_key)

    @classmethod
    def chain_find_first(cls, *registries: Self, sort_key, **criteria) -> Optional[EntityT]:
        # chain_find_one() without a sort_key is just reg[0].find_one()
        return next(cls.chain_find_all(*registries, sort_key=sort_key, **criteria), None)

    # CONVENIENCE ITERABLES

    def all(self) -> list[EntityT]:
        return list(self)

    def all_labels(self) -> list[str]:
        return [str(i.label) for i in self]

    def all_tags(self) -> set[Tag]:
        return set(itertools.chain.from_iterable(i.tags for i in self))

    # STRUCTURING

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        items = data.pop("items")
        obj = super().structure(data)
        for e in items:
            obj.add( super().structure(e) )
        return obj

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        # data is marked private, so it will not be included by model dump
        data['items'] = [ e.unstructure() for e in self.all() ]
        return data
