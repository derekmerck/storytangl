# tangl/core/registry.py
from __future__ import annotations
from typing import TypeVar, Generic, Iterator, Iterable, Optional, Self
from uuid import UUID
import itertools
import logging
from functools import cached_property

from pydantic import Field

from tangl.type_hints import UnstructuredData
from .entity import Entity
from .selector import Selector

logger = logging.getLogger(__name__)

ET = TypeVar('ET', bound=Entity)

class Registry(Entity, Generic[ET]):
    """
    Indexed collection with selection and chaining.

    Registry is the primary mechanism for groups of intra-related entities to be managed and serialized.

    **Rules:**
    - Registries are the canonical dereference mechanism for ID-linked graphs
    - `chain_find_all` is Core's primitive for layered composition

    - **Indexing**
    - Registries are indexed by `uid: UUID`.
    - Broader identifier matching is done via selection (`find_*` with `Selector(identifier=...)` / `has_identifier` criteria), not via `get()`.

    Registry is an "Owning boundary" that may embed nested unstructurable children.  Owning
    boundaries must handle un/structuring children explicitly and guarantee round-trips.

    Example:
        >>> a = Entity(label="abc"); b = Entity(label="def")
        >>> r = Registry(); r.add(a); r.add(b)
        >>> len(r.members)
        2
        >>> r.get(a.uid)  # indexed by uid
        <Entity:abc>
        >>> r.all_labels() == {"abc", "def"}
        True
        >>> s = Selector.from_identifier("abc")
        >>> r.find_one(s)
        <Entity:abc>
        >>> c = Entity(label="abc")
        >>> q = Registry(); q.add(c)
        >>> list( Registry.chain_find_all(r, q, selector=s) ) == [a, c]
        True
        >>> data = r.unstructure()
        >>> rr = Registry.structure(data)
        >>> len(rr.members)
        2
        >>> r is not rr and r == rr  # compare by value
        True
        >>> rr.add(Entity()) # compare by value includes members field
        >>> rr != r
        True
    """

    # todo: should be unstructure=False, if we exclude it doesn't get used in eq
    members: dict[UUID, ET] = Field(default_factory=dict, exclude=True)

    def add(self, value: ET, _ctx = None):
        if hasattr(value, 'set_registry'):
            value.set_registry(self)
        if _ctx is not None:
            # chance to modify before inserting
            from .dispatch import do_add_item
            value = do_add_item(registry=self, item=value, ctx=_ctx)
        self.members[value.uid] = value

    def remove(self, key: UUID, _ctx = None):
        item = self.members.pop(key, None)
        if item is not None and hasattr(item, 'set_registry'):
            item.set_registry(None)
        if _ctx is not None:
            # chance to review before discarding
            from .dispatch import do_remove_item
            do_remove_item(registry=self, item=item, ctx=_ctx)
        # or del self.members[key] if you want to throw a key error

    def get(self, key: UUID, _ctx = None):
        item = self.members.get(key, None)
        if _ctx is not None:
            # chance to modify before returning
            from .dispatch import do_get_item
            item = do_get_item(registry=self, item=item, ctx=_ctx)
        return item
        # or return self.members[key] if you want to throw a key error

    def all_labels(self):
        return set([v.label for v in self.members.values()])

    @classmethod
    def _filter_and_sort(cls, values, selector = None, sort_key = None) -> Iterator[ET]:
        if selector is not None:
            values = selector.filter(values)
        if sort_key is None:
            yield from values
        else:
            yield from sorted(values, key=sort_key)

    def find_all(self, selector: Selector = None, sort_key = None) -> Iterator[ET]:
        values = self.members.values()
        return self._filter_and_sort(values, selector=selector, sort_key=sort_key)

    def find_one(self, selector: Selector = None, sort_key= None ) -> Optional[ET]:
        return next(self.find_all(selector, sort_key=sort_key), None)

    @classmethod
    def chain_find_all(cls, *registries: Self, selector: Selector = None, sort_key = None) -> Iterator[ET]:
        values = itertools.chain.from_iterable(r.members.values() for r in registries)
        return cls._filter_and_sort(values, selector=selector, sort_key=sort_key)

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        data["members"] = [v.unstructure() for v in self.members.values()]
        return data

    @classmethod
    def structure(cls, data: UnstructuredData):
        _members = data.pop("members", [])
        obj = super().structure(data)  # type: Self
        for v in _members:
            obj.add(Entity.structure(v))
        return obj

    # Provide mapping interface

    def values(self) -> Iterable[ET]:
        return self.members.values()

    def clear(self):
        self.members.clear()

    def __len__(self) -> int:
        return len(self.members)

    def __bool__(self) -> bool:
        return len(self.members) > 0

    def __iter__(self) -> Iterator[ET]:
        # iter values not keys, gets '__contains__(item)' for free
        return iter(self.members.values())

    def __getitem__(self, key: UUID):
        return self.get(key)

    def __delitem__(self, key: UUID):
        self.remove(key)

    def __setitem__(self, key, value):
        # refer to add
        raise KeyError(f"May not set items directly by key.  Use `registry.add(item)` instead.")


# Additional bases for entities that can be gathered in a registry

class RegistryAware(Entity):
    """
    Entities that are managed by a single registry can be auto-registered.

    Registry-aware entities never hold direct pointers to other members of their registry. They store indirect references to other members via UUIDs.  These are usually resolved lazily on property access.

    Example:
        >>> a = RegistryAware(); r = Registry(); r.add(a)
        >>> a.registry == r
        True
        >>> Registry().add(a)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        ValueError: Registry is already set
    """

    registry: Registry[RegistryAware] = Field(None, exclude=True)

    def set_registry(self, registry: Registry):
        if self.registry is not None and self.registry is not registry:
            raise ValueError("Registry is already set")
        self.registry = registry


class EntityGroup(RegistryAware):
    """
    RegistryAware Entities can reference peers in the same group
    by id, entities _never_ carry direct pointers to other entities
    to avoid structure/unstructure complexity.

    This looks like a registry, but it does not claim ownership of
    any items.  It is a registry item itself and refers to its members
    by uid, as peers.

    Groups live _in_ the same registry that they provide a view of.

    Example:
        >>> e = EntityGroup(registry=Registry())
        >>> e.add_members(RegistryAware(label="abc"), RegistryAware(label="def"), RegistryAware(label="ghi"))
        >>> [ m.get_label() for m in e.members() ]
        ['abc', 'def', 'ghi']
        >>> a = e.member(Selector.from_identifier("abc"))
        >>> e.has_member(a)
        True
        >>> e.remove_member(a)
        >>> e.has_member(a)
        False
        >>> [ m.get_label() for m in e.members() ]
        ['def', 'ghi']
    """
    member_ids: list[UUID] = Field(default_factory=list)

    def member(self, selector: Selector = None, sort_key = None) -> ET:
        return next(self.members(selector, sort_key=sort_key), None)

    def members(self, selector: Selector = None, sort_key = None) -> Iterator[ET]:
        items = (self.registry.get(uid) for uid in self.member_ids)
        selector = selector or Selector()
        if self.registry is not None:
            return self.registry._filter_and_sort(items, selector=selector, sort_key=sort_key)
        raise ValueError("Group registry is not set")

    def add_member(self, item: RegistryAware):
        if item is self:
            raise ValueError("Group cannot add itself to itself")
        self.registry.add(item)
        self.member_ids.append(item.uid)

    def add_members(self, *items: RegistryAware):
        for item in items:
            self.add_member(item)

    def remove_member(self, item: RegistryAware):
        if item.uid in self.member_ids:
            self.member_ids.remove(item.uid)

    def has_member(self, item: RegistryAware) -> bool:
        # for selection criteria, uses __contains__ compare-by-uid
        return item in self

    def __iter__(self) -> Iterator[RegistryAware]:
        # get __contains__ for free
        return iter(self.members())

    def __contains__(self, item: RegistryAware) -> bool:
        # although this is better than iter, b/c it doesn't have to deref id's
        return item.uid in self.member_ids


class HierarchicalGroup(EntityGroup):

    @cached_property
    def parent(self) -> Self:
        return self.registry.find_one(Selector(has_kind=HierarchicalGroup, has_member=self))

    # Just aliases to membership ops
    def children(self, selector: Selector) -> Iterator[Self]:
        return self.members(selector=selector)

    def add_child(self, item: Self):
        # Enforce uniqueness of membership
        if item.parent is not None:
            item.parent.remove_child(item)
        return self.add_member(item)

    def remove_child(self, item: ET):
        self.remove_member(item)
        if hasattr(item, "parent"):
            # invalidate the cached parent
            delattr(item, "parent")

    @property
    def root(self) -> Self:
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def ancestors(self) -> list[Self]:
        root = self
        result = []
        while root.parent is not None:
            result.append(root)
            root = root.parent
        return result

    @property
    def path(self) -> str:
        labels = [a.get_label() for a in self.ancestors]
        result = ".".join(reversed(labels))
        return result
