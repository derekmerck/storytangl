from uuid import UUID, uuid4
from typing import Any, List

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

class Identifiable(BaseModel):
    uid: UUID = Field(default_factory=uuid4)

@dataclass
class ProvisionKey:
    domain: str
    name: str
    def __hash__(self): return hash((self.domain, self.name))

class Providable(BaseModel):
    requires: set[ProvisionKey] = Field(default_factory=set)
    provides: set[ProvisionKey] = Field(default_factory=set)

    # want to add tags of the form pvds@key:value to provision keys
    # and reqs@key:value to requirements

class Entity(Identifiable):
    label: str | None = None
    tags: set[str] = Field(default_factory=set)
    locals: dict[str, Any] = Field(default_factory=dict)

    # ultra‑simple matcher for robust find
    def matches(self, **criteria):
        return all(getattr(self, k, None) == v for k, v in criteria.items())
