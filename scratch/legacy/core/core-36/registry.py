# tangl/core/registry.py
"""
# tangl.core.registry

Tiny UID→object store with predicate helpers and a DTO snapshot format.

**Why a hand-rolled registry?**
- We want a **predictable** iteration order and a tiny API surface for tests/tools.
- It’s decoupled from the data model (no reliance on Pydantic internals).
- `Graph` composes one `Registry[GraphItem]` rather than inheriting from it.

Downstream:
- `Graph.items` is a `Registry[GraphItem]`.
- Storage uses `to_dto`/`from_dto` to persist/restore items by FQN.
"""
from __future__ import annotations
from typing import Iterator, Optional, TypeVar, Generic, Callable
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

from .entity import Entity

T = TypeVar("T", bound=Entity)

class Registry(BaseModel, Generic[T]):
    """
    Minimal, in-memory registry with:

    - `add/get/remove/iter/len` – core operations.
    - `find_all/find_one` – ergonomic filtered scans (`matches` + optional predicate).
    - `to_dto/from_dto` – portable structural snapshot (FQN + data) for storage.

    **Why not expose dict directly?** Keeping the API tiny lets us evolve indexing later
    (e.g., add a fast label map) without breaking call sites.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    _items: dict[UUID, T] = PrivateAttr(default_factory=dict)

    # ---- basic ----
    def add(self, item: T) -> None:
        self._items[item.uid] = item

    def remove(self, uid: UUID) -> None:
        self._items.pop(uid, None)

    def get(self, uid: UUID) -> Optional[T]:
        return self._items.get(uid)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __len__(self):
        return len(self._items)

    def find(self, filt: Callable[[T], bool] | None = None, **criteria) -> Iterator[T]:
        filt = filt or (lambda _: True)
        for item in self:
            if item.matches(**criteria) and filt(item):
                yield item

    def find_one(self, filt: Callable[[T], bool] | None = None, **criteria) -> Optional[T]:
        return next(self.find_all(filt=filt, **criteria), None)

    # ---- DTO snapshot ----
    def to_dto(self) -> dict:
        return {"items": [it.to_dto() for it in self]}

    @classmethod
    def from_dto(cls, dto: dict, resolver: Callable[[str], type]) -> Registry[T]:
        reg = cls()
        for entry in dto.get("items", []):
            cls_fqn = entry["cls"]; data = entry["data"]
            typ = resolver(cls_fqn)
            reg.add(typ(**data))  # type: ignore[arg-type]
        return reg
