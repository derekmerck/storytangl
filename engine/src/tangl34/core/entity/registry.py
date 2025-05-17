from typing import TypeVar, Generic, Dict, Optional, List, Iterator
from uuid import UUID

from .entity import Entity

EntityT = TypeVar("EntityT", bound=Entity)

class Registry(Generic[EntityT]):
    """Simple runtime registry with optional constraints and named lookup."""
    def __init__(self):
        self._items: Dict[UUID, EntityT] = {}

    def add(self, item: EntityT) -> None:
        self._items[item.uid] = item

    def remove(self, item: EntityT | UUID) -> None:
        if not issubclass(item, UUID):
            item = getattr(item, "uid", None)
        self._items.pop(item, None)

    def get(self, uid: UUID) -> Optional[EntityT]:
        return self._items.get(uid)

    def all(self) -> List[EntityT]:
        return list(self._items.values())

    def find_one(self, **criteria) -> Optional[EntityT]:
        return next(item for item in self if item.match(**criteria))

    def find_all(self, **criteria) -> List[EntityT]:
        return [item for item in self if item.match(**criteria)]

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return len(self) > 0

    def __iter__(self) -> Iterator[EntityT]:
        return iter(self._items.values())

