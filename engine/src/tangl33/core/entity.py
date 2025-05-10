"""
tangl.core.entity
=================

Base structural element for the StoryTangl system.

An Entity is a lightweight identified data container with:
- A UUID for reliable identity
- An optional label for human readability
- A set of tags for flexible categorization
- A standard matching protocol for robust filtering

Entities are the atomic building blocks underlying StoryTangl's graph structure.
Their simplified implementation prioritizes:
- Memory efficiency for large graphs
- Fast matching for search operations
- Minimal dependencies for serialization

Unlike the former Entity class, this new implementation uses dataclasses
and emphasizes composition over inheritance for extensibility.

See Also
--------
Registry: Collection of searchable entities
Node: An entity with graph relationships
Graph: Connected collection of nodes
"""

from uuid import uuid4, UUID
from dataclasses import dataclass, field
from typing import Any

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
