from typing import TypeVar, Generic, Dict, Optional, List, Iterator, Self
from uuid import UUID

from pydantic import PrivateAttr

from ..type_hints import UnstructuredData
from .entity import Entity

EntityT = TypeVar("EntityT", bound=Entity)

class Registry(Entity, Generic[EntityT]):
    """
    Registry class for managing and organizing multiple entities.

    The Registry class provides methods to add, remove, retrieve, and search
    entities by their IDs or specific criteria. It uses a private
    dictionary to manage entities and implements iterable and boolean
    interfaces for convenience.

    :ivar _items: Private dictionary storing entities with their UUIDs as keys.
    :type _items: dict[UUID, EntityT]
    """

    _items: dict[UUID, EntityT] = PrivateAttr(default_factory=dict)

    def add(self, item: EntityT) -> None:
        self._items[item.uid] = item

    def remove(self, item: EntityT | UUID) -> None:
        if not isinstance(item, UUID):
            item = getattr(item, "uid", None)
        self._items.pop(item, None)

    def get(self, uid: UUID) -> Optional[EntityT]:
        return self._items.get(uid)

    def find_one(self, **criteria) -> Optional[EntityT]:
        return next(item for item in self if item.match(**criteria))

    def find_all(self, **criteria) -> List[EntityT]:
        return [item for item in self if item.match(**criteria)]

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def __iter__(self) -> Iterator[EntityT]:
        return iter(self._items.values())

    def clear(self):
        self._items.clear()

    @classmethod
    def structure(cls, data) -> Self:
        items = data.pop("items")
        obj = super().structure(data)
        for e in items:
            obj.add( super().structure(e) )
        return obj

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        data['items'] = [ e.unstructure() for e in self.values() ]
        return data
