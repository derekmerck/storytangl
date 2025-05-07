from uuid import UUID, uuid4
from typing import Any, List

from pydantic import BaseModel, Field

from .requirement import Providable
from .context_provider import ContextProvider

class Identifiable(BaseModel):
    uid: UUID = Field(default_factory=uuid4)


class Entity(Providable, Identifiable):
    label: str | None = None
    tags: set[str] = Field(default_factory=set)
    locals: dict[str, Any] = Field(default_factory=dict)

    # all entities have context providers -- they provide their locals at least
    context_providers: list[ContextProvider] = Field(default_factory=list)

    # ultra‑simple matcher for robust find
    def matches(self, **criteria):
        return all(getattr(self, k, None) == v for k, v in criteria.items())

    def __repr__(self):
        return f"{self.__class__.__name__}({self.label!r})"
