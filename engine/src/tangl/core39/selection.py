from __future__ import annotations
from typing import TypeVar, Iterator, Iterable

from pydantic import BaseModel, Field

from tangl.type_hints import StringMap
from .entity import Entity

##############################
# SELECTION
##############################

ET = TypeVar('ET', bound=Entity)

class Selector(BaseModel):
    criteria: StringMap = Field(default_factory=dict)

    def update(self, **updates: StringMap) -> None:
        self.criteria.update(updates)

    def match(self, item: Entity) -> bool:
        for k, v in self.criteria.items():
            attr = getattr(item, k)
            if attr is None:
                return False
            elif callable(attr):
                return attr(v)
            elif attr != v:
                return False
            return True
        return True

    def select_all(self, items: Iterable[ET]) -> Iterator[ET]:
        return filter(lambda item: self.match(item), items)

