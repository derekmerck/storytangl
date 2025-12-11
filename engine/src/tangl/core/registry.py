# tangl/core/registry.py
"""
tangl.core.registry
===================

Collection management for entities with robust search capabilities.

The Registry provides a generic dictionary-like container for Entity
objects with enhanced retrieval options:

- UUID-based direct access for performance-critical operations
- Criteria-based flexible search for dynamic discovery
- Type safety via generic parameters
- Composition over inheritance for extensibility

The Registry underpins the core StoryTangl graph management.

This component is foundational as it enables decoupling between
storage patterns and retrieval logic, letting capabilities
find requirements and vice versa without direct references.

Registry is subclassed for multiple different applications.
- **StreamRegistry** indexes sequential records with built-in sorting, slicing,
  and channel filtering
- **BehaviorRegistry** indexes handlers and has built-in execution pipelines
  and job receipts
- **MediaRegistry** indexes external resources into singleton MediaRecords,
  which can be dereferenced in the service layer to retrieve the original
  data or client-relative path to it
"""

from typing import TypeVar, Generic, Optional, Iterator, overload, Self
from uuid import UUID
from collections import Counter
import itertools
import logging
from contextvars import ContextVar
from contextlib import contextmanager

from pydantic import Field

from tangl.type_hints import StringMap, Tag
from .entity import Entity, Selectable

logger = logging.getLogger(__name__)

VT = TypeVar("VT", bound=Entity)  # registry value type
FT = TypeVar("FT", bound=Entity)  # find type within registry
ST = TypeVar("ST", bound=Selectable)


class Registry(Entity, Generic[VT]):
    """
    Registry(data: dict[~uuid.UUID, Entity])

    Generic searchable collection of :class:`Entity`.

    Why
    ----
    Provides a flexible alternative to raw dicts: lookup by UUID, label, tags,
    or arbitrary predicates. Serves as the foundation for higher-level managers
    like graphs, record streams, and handler registries.

    Key Features
    ------------
    * **UUID-based access** for fast, deterministic retrieval.
    * **Criteria-based search** (:meth:`find_all`, :meth:`find_one`) for
      flexible queries.
    * **Chaining** across multiple registries via
      :meth:`chain_find_all` / :meth:`chain_find_one`.
    * **Selection** logic (:meth:`select_for`) for inverse-matching entities.

    API
    ---
    - :meth:`add` / :meth:`remove` – manage membership
    - :meth:`find_all(**criteria)<find_all>` – yield all matches
    - :meth:`find_one(**criteria)<find_one>` – yield first match
    - :meth:`chain_find_all` – search across registries
    - :meth:`all_labels`, :meth:`all_tags` – summarization helpers
    """

    data: dict[UUID, VT] = Field(default_factory=dict,
                                 json_schema_extra={'serialize': False})
    # don't bother serializing this field b/c we will include it explicitly
    # but do use it for comparison (using `exclude=True` would cover both).

    def add(self, entity: VT) -> None:
        """Add an entity to the registry.

        Raises
        ------
        ValueError
            If a different entity with the same UUID already exists.
        """
        if entity.uid in self.data:
            existing = self.data[entity.uid]
            if existing is entity:
                return
            raise ValueError(
                f"Entity {entity.uid} already exists in registry. "
                f"Existing: {existing!r}, attempted: {entity!r}"
            )
        self.data[entity.uid] = entity

    def get(self, key: UUID) -> Optional[VT]:
        if isinstance(key, str):
            raise ValueError(
                f"Use find_one(label='{key}') instead of get('{key}') to get-by-label"
            )
        return self.data.get(key)

    def remove(self, key: VT | UUID):
        if isinstance(key, Entity):
            key = key.uid
        if not isinstance(key, UUID):
            raise ValueError(f"Wrong type for remove key {key}")
        self.data.pop(key)

    @property
    def is_dirty(self) -> bool:
        # One bad apple ruins the barrel
        return self.is_dirty_ or self.any_dirty()

    def any_dirty(self) -> bool:
        """Check if any entity in this registry is marked dirty."""
        return any(entity.is_dirty for entity in self.data.values())

    def find_dirty(self) -> Iterator[VT]:
        """Yield all dirty entities in the registry."""
        return (entity for entity in self.data.values() if entity.is_dirty)

    # -------- FIND IN COLLECTION ----------

    @overload
    def find_all(self, *, is_instance: FT, **criteria) -> Iterator[FT]:
        ...

    @overload
    def find_all(self, **criteria) -> Iterator[VT]:
        ...

    def find_all(self, sort_key = None, **criteria):
        iter_values = Entity.filter_by_criteria(self.values(), **criteria)
        if sort_key is None:
            yield from iter_values
        else:
            yield from sorted(iter_values, key=sort_key)

    def find_one(self, **criteria) -> Optional[VT]:
        if "uid" in criteria:
            return self.get(criteria["uid"])
        return next(self.find_all(**criteria), None)

    # -------- CHAINED FIND ----------

    @classmethod
    def chain_find_all(cls, *registries: Self, sort_key = None, **criteria) -> Iterator[VT]:
        with _chained_registries(*registries):  # make registries available to inner calls
            iter_values = itertools.chain.from_iterable(
                r.find_all(**criteria) for r in registries)
            if sort_key is None:
                yield from iter_values
            else:
                yield from sorted(iter_values, key=sort_key)

    @classmethod
    def chain_find_one(cls, *registries: Self, sort_key = None, **criteria) -> Optional[VT]:
        if sort_key is None:
            logger.warning("chain_find_one with no sort key is legal, but it may not be what you want, it is just reg[0].find_one()")
        return next(cls.chain_find_all(*registries, sort_key=sort_key, **criteria), None)

    # -------- FIND SATISFIERS -----------

    def select_all_for(self, selector: Entity, sort_key = None, **inline_criteria) -> Iterator[ST]:
        # filter will gracefully fail if VT is not a Selectable
        iter_values = Selectable.filter_for_selector(self.values(), selector=selector, **inline_criteria)
        if sort_key is None:
            yield from iter_values
        else:
            yield from sorted(iter_values, key=sort_key)

    def select_one_for(self, selector: Entity, **inline_criteria) -> Optional[ST]:
        return next(self.select_for(selector, **inline_criteria), None)

    @classmethod
    def chain_select_all_for(cls, *registries: Self, selector: Entity, sort_key = None, **inline_criteria) -> Iterator[ST]:
        with _chained_registries(*registries):  # make registries available to inner calls
            iter_values = itertools.chain.from_iterable(
                r.select_all_for(selector, **inline_criteria) for r in registries)
            if sort_key is None:
                yield from iter_values
            else:
                yield from sorted(iter_values, key=sort_key)

    @classmethod
    def chain_select_one_for(cls, *registries: Self, selector: Entity, **inline_criteria) -> Optional[ST]:
        return next(cls.chain_select_all_for(*registries, selector=selector, **inline_criteria), None)

    # -------- DELEGATE MAPPING METHODS -----------

    def keys(self) -> Iterator[UUID]:
        return iter(self.data.keys())

    def values(self) -> Iterator[VT]:
        return iter(self.data.values())

    def __bool__(self) -> bool:
        return bool(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[VT]:
        return iter(self.data.values())

    def clear(self) -> None:
        self.data.clear()

    def __contains__(self, key: UUID | str | VT) -> bool:
        if isinstance(key, UUID):
            return key in self.data
        elif isinstance(key, Entity):
            return key in self.data.values()
        elif isinstance(key, str):
            return key in self.all_labels()
        raise ValueError(f"Unexpected key type for contains {type(key)}")

    # -------- SUMMARY HELPERS ----------

    def all_labels(self) -> list[str]:
        return list({x.get_label() for x in self.data.values() if x.get_label() is not None})

    def all_tags(self) -> set[Tag]:
        return set(itertools.chain.from_iterable(i.tags for i in self))

    def all_tags_frequency(self) -> Counter[Tag]:
        return Counter(itertools.chain.from_iterable(i.tags for i in self))

    # -------- EVENT SOURCED REPLAY ----------
    # todo: I think this is redundant, only WatchedRegistry add/get/remove
    #       is monitored, so we would only get echo if we are restoring via
    #       a wrapped object?

    def _add_silent(self, entity: VT):
        self.data[entity.uid] = entity

    def _get_silent(self, key: UUID) -> Optional[VT]:
        return self.data.get(key)

    def _remove_silent(self, key: VT | UUID):
        if isinstance(key, Entity):
            key = key.uid
        self.data.pop(key)

    # -------- STRUCTURING AND UNSTRUCTURING ----------

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        # Be careful of nested delegation here
        _data = data.pop("_data", {})  # local copy
        obj = super().structure(data)  # type: Self
        for v in _data:
            _obj = Entity.structure(v)
            obj.add(_obj)
        return obj

    def model_dump(self, **kwargs) -> StringMap:
        data = super().model_dump(**kwargs)  # ignores data
        data["_data"] = []
        for v in self.data.values():
            data['_data'].append(v.unstructure())
        return data

# For chain-find/select, provide the entire list of participating registries
# in the call stack.  Enables chain-order sort keys for items that know what registry they came from.

_CHAINED_REGISTRIES: ContextVar[list[Registry] | None] = ContextVar(
    "_CHAINED_REGISTRIES", default=None
)

@contextmanager
def _chained_registries(*registries: Registry) -> list[Registry] | None:
    token = _CHAINED_REGISTRIES.set(list(registries))
    try:
        yield
    finally:
        _CHAINED_REGISTRIES.reset(token)

