from uuid import uuid4, UUID
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class Entity:
    uid: UUID = field(default_factory=uuid4)
    label: str | None = None
    tags: set[str] = field(default_factory=set)

    # ultra‑simple matcher for robust find
    def matches(self, **criteria):
        return all(getattr(self, k, None) == v for k, v in criteria.items())

    def __repr__(self):
        return f"{self.__class__.__name__}({self.label!r})"
