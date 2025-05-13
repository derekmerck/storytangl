from typing import TypeVar, Generic, Dict, Optional, List
from uuid import UUID

from .entity import Entity

T = TypeVar("T", bound=Entity)

class Registry(Generic[T]):
    """Simple runtime registry with optional constraints and named lookup."""
    def __init__(self):
        self._items: Dict[UUID, T] = {}

    def register(self, item: T) -> None:
        self._items[item.uid] = item

    def unregister(self, item: T | UUID) -> None:
        if not issubclass(item, UUID):
            item = getattr(item, "uid", None)
        self._items.pop(item, None)

    def get(self, uid: UUID) -> Optional[T]:
        return self._items.get(uid)

    def all(self) -> List[T]:
        return list(self._items.values())

    def find(self, **features) -> List[T]:
        return [item for item in self._items.values() if item.match(**features)]