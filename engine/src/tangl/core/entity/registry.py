"""
tangl.core.registry
===================

Collection management for entities with robust search capabilities.

The Registry provides a generic dictionary-like container for Entity
objects with enhanced retrieval options:

- UUID-based direct access for performance-critical operations
- Criteria-based flexible search for dynamic discovery
- Type safety via generic parameters
- Composition over inheritance for extensibility

The Registry underpins the core StoryTangl graph management.

This component is foundational as it enables decoupling between
storage patterns and retrieval logic, letting capabilities
find requirements and vice versa without direct references.
"""

from typing import TypeVar, Generic, Optional, Iterator, Self, Callable
from uuid import UUID
import itertools
from collections import Counter

from pydantic import PrivateAttr

from tangl.type_hints import UnstructuredData, Tag
from .entity import Entity # has uid, label, tags

EntityT = TypeVar("EntityT", bound=Entity)

class RegistryP(Entity, Generic[EntityT]):
    def add(self, entity: EntityT): ...
    def remove(self, item: EntityT | UUID) -> None: ...
    def get(self, uid: UUID) -> Optional[EntityT]: ...
    def clear(self): ...

    def find_one(self, filt=None, sort_key=None, **criteria) -> Optional[EntityT]: ...
    def find_all(self, filt=None, sort_key=None, **criteria) -> Iterator[EntityT]: ...

    @classmethod
    def chain_find_one(cls, *registries: Self, filt=None, sort_key=None, **criteria) -> Optional[EntityT]: ...
    @classmethod
    def chain_find_all(cls, *registries: Self, filt=None, sort_key=None, **criteria) -> Iterator[EntityT]: ...

class Registry(Entity, Generic[EntityT]):

    _items: dict[UUID, EntityT] = PrivateAttr(default_factory=dict)

    # -------- BASIC API ----------

    def add(self, item: EntityT) -> None:
        if not hasattr(item, "uid"):
            raise ValueError(f"Cannot register objects without a uid {type(item)}")
        self._items[item.uid] = item

    def add_all(self, *items: EntityT):
        for item in items:
            self.add(item)

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

    def find_all(self, sort_key=None, filt: Callable[[EntityT], bool] = None, **criteria) -> Iterator[EntityT]:
        filt = filt or (lambda x: True)
        if sort_key is None:
            yield from (item for item in self if item.matches(**criteria) and filt(item))
        else:
            yield from (item for item in sorted(self, key=sort_key) if item.matches(**criteria) and filt(item))

    def find_one(self, filt=None, sort_key=None, **criteria) -> Optional[EntityT]:
        if "uid" in criteria:
            return self.get(criteria["uid"])
        return next(self.find_all(filt=filt, sort_key=sort_key, **criteria), None)

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

    @property
    def is_dirty(self):
        # One bad apple ruins the barrel
        return self.is_dirty_ or \
            any([item.is_dirty for item in self])

    # -------- CHAINED FIND ----------

    @classmethod
    def chain_find_all(cls, *registries: Self, filt=None, sort_key=None, **criteria) -> Iterator[EntityT]:
        reg_iter = itertools.chain.from_iterable(
            r.find_all(filt=filt, **criteria) for r in registries)
        if sort_key is None:
            yield from reg_iter
        else:
            yield from sorted(reg_iter, key=sort_key)

    @classmethod
    def chain_find_one(cls, *registries: Self, filt=None, sort_key=None, **criteria) -> Optional[EntityT]:
        # chain_find_one() without a sort_key is just reg[0].find_one()
        return next(cls.chain_find_all(*registries, filt=filt, sort_key=sort_key, **criteria), None)

    # -------- CONVENIENCE ITERABLES ----------

    def keys(self) -> list[UUID]:
        return list(self._items.keys())

    def all(self) -> list[EntityT]:
        return list(self)

    def all_labels(self) -> list[str]:
        return [str(i.label) for i in self]

    def all_tags(self) -> set[Tag]:
        return set(itertools.chain.from_iterable(i.tags for i in self))

    def all_tags_frequency(self) -> Counter[Tag]:
        return Counter(itertools.chain.from_iterable(i.tags for i in self))

    # -------- STRUCTURING ----------

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
