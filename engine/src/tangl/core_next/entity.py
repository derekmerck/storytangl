from uuid import UUID, uuid4
from typing import Any, List

from pydantic import BaseModel, Field


class Identifiable(BaseModel):
    uid: UUID = Field(default_factory=uuid4)


class Entity(Identifiable):
    label: str | None = None
    tags: set[str] = Field(default_factory=set)
    locals: dict[str, Any] = Field(default_factory=dict)

    # ultra‑simple matcher for robust find
    def matches(self, **criteria):
        return all(getattr(self, k, None) == v for k, v in criteria.items())

    def __repr__(self):
        return f"{self.__class__.__name__}({self.label!r})"
