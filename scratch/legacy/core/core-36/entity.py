# tangl/core/entity.py
"""
# tangl.core.entity

Minimal, portable records for the story IR.

**Why these shapes?**

- We keep entities tiny and **runtime-agnostic** so the same IR can be replayed in other runtimes later.
- `Entity.to_dto()` embeds a **fully-qualified class name (FQN)** so we can reconstruct objects without pickle
  (used by `Graph.to_dto()`/`from_dto()` and storage backends).
- `Node.locals` is the only author-writable per-node dict that the VM exposes in **scoped namespaces**
  (see `tangl.vm.scopes.assemble_namespace`); everything else should change via **Effects**.

**Downstream dependencies**

- `tangl.core.graph.Graph` stores `GraphItem`s and keeps separate adjacency.
- `tangl.vm.patch.apply_patch` constructs `Node`/`Edge` from DTO/FQN during replay.
- `tangl.vm.scopes` reads `Node.locals` and `Node.tags` (e.g. `domain:*`) to assemble scope.
"""

from __future__ import annotations
from typing import Optional, Any, Iterable, Iterator, Type, ClassVar
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
from .types import Tag

def fqn(obj_or_type: Any) -> str:
    """
    Return a stable **module:qualname** for a class or instance.

    **Why?** We serialize by FQN (not pickle) to keep on-disk / over-the-wire payloads portable.
    During replay, the VM calls a resolver (usually `importlib`) to map FQN → class.
    """
    t = obj_or_type if isinstance(obj_or_type, type) else type(obj_or_type)
    return f"{t.__module__}:{t.__qualname__}"

class Entity(BaseModel):
    """
    Base record for all graph objects.

    - `uid`: globally unique identifier (UUID4).
    - `label`: optional human-readable name (used by authors and tests).
    - `tags`: freeform string tags; **reserved** `domain:*` tags activate domain providers (see `vm.scopes`).

    ### Why not richer behavior here?
    The mutation path is **event-sourced**: handlers emit Effects, and
    `vm.patch.apply_patch` updates the graph. Keeping Entity “dumb” avoids side-effects in serialization.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    uid: UUID = Field(default_factory=uuid4)
    label: Optional[str] = None
    tags: set[Tag] = Field(default_factory=set)

    def matches(self, filt=None, **criteria) -> bool:
        """
        Small helper for registry queries.

        - `criteria` are exact equality checks on attributes self.k == v, or has_k(v) -> bool callables.
        - `filt` is an optional predicate for more complex checks.

        Used by `Registry.find_*` to keep calling code terse in tests and tools.
        """
        if filt and not filt(self):
            return False
        for k, v in criteria.items():
            attr = getattr(self, k, None)
            if k.startswith("has_") and callable(attr):
                if not attr(v):
                    return False
            elif getattr(self, k, None) != v:
                return False
        return True

    def has_cls(self, obj_cls: Type[Entity]) -> bool:
        return isinstance(self, obj_cls)

    def has_tags(self, *tags) -> bool:
        """
        Convenience membership check for `tags`.

        **Note:** Domain activation depends on `tags` with the `domain:` prefix,
        see `Facts.active_domains_along` and `vm.scopes`.
        """
        return set(tags).issubset(self.tags)

    def to_dto(self) -> dict:
        """
        Serialize to a portable DTO: `{"cls": FQN, "data": <model_dump>}`.

        **Why?** This allows:
        - Pickle-free snapshots.
        - Cross-runtime rehydration by resolving the FQN at load time.

        Downstream: `Graph.to_dto()` nests these; `persist.ser` handles encoding (pickle/orjson/etc).
        """
        data = self.model_dump(exclude_none=True, exclude_unset=True)
        # uid is still considered UNSET even if the factory is called, so we have
        # to include it manually
        data["uid"] = self.uid
        return {"cls": fqn(self), "data": data}

class GraphItem(Entity):
    """
    Marker for IR items that live on a `Graph` (currently `Node` and `Edge`).
    Separated so `Registry` can be generic over `GraphItem` and tooling can type-narrow safely.
    """
    pass

class Node(GraphItem):
    """
    Semantic node in the story graph.

    - `locals`: dict injected into the **scope namespace** in `vm.scopes.assemble_namespace`.
      Precedence is `local → ancestors → domain vars → globals`.

    **Why keep `locals` here (and not in a separate store)?**
    - It keeps *author ergonomics* high (`ctx.ns["foo"]`, `player.hp`, etc.) without complicating the write path.
    - It doesn’t compromise determinism because `locals` changes still go through Effects (`SET_ATTR`).
    """
    locals: dict[str, Any] = Field(default_factory=dict)

class Edge(GraphItem):
    """
    Topology link between two nodes.

    - `src_id`, `dst_id`: UIDs to avoid in-memory cycles.
    - `kind`: string label. The reserved kind `"contains"` builds the **structural tree**
      used for scopes (ancestor chain resolution in `Facts`).

    **Why IDs not references?** Replay reconstructs objects by DTO; keeping edges id-based
    keeps snapshots/persisters simple and avoids object graph headaches.
    """
    src_id: UUID
    dst_id: UUID
    kind: str
