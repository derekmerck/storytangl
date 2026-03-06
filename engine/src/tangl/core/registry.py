# tangl/core/registry.py
# language=markdown
"""
# Registries and groups (v38)

This module defines **ownership** and **membership** primitives for core.

- A **Registry** owns a set of entities and is the canonical dereference boundary for
  ID-linked structures.
- A **Group** is itself a registry member that stores *only* member UUIDs, and resolves
  those UUIDs back to entities via its owning registry.

## Two related but distinct ideas

1) **Owning boundary** (Registry)

A registry is responsible for:

- indexing members by `uid: UUID`
- selection via `Selector` (`find_one`, `find_all`, `chain_find_all`)
- structuring/unstructuring its members for persistence
- binding registry-aware items (`bind_registry`)

2) **Views over a registry** (Groups)

Groups do **not** own members. They only:

- maintain `member_ids: list[UUID]`
- provide iterators that dereference `member_ids` through the registry

This keeps un/structuring simple: members are persisted once in the registry, and groups
persist only the UUID references.

## Hook points

Registry operations accept an optional `_ctx` which higher layers may use to trigger
behavior hooks (`do_add_item`, `do_get_item`, `do_remove_item`). Core remains usable
without a dispatch system.

See Also
--------
- `tangl.core.graph.Graph` for a topology-specialized registry.
- `tangl.core.template.TemplateRegistry` for template ownership and lookup.
- `chain_find_one` was intentionally removed; use
  `next(Registry.chain_find_all(...), None)` when needed.

"""
from __future__ import annotations
from typing import Any, TypeVar, Generic, Iterator, Iterable, Optional, Self, TypeAlias
from uuid import UUID
import itertools
import logging
from functools import cached_property

from pydantic import Field, PrivateAttr, SkipValidation

from tangl.type_hints import UnstructuredData
from .entity import Entity
from .selector import Selector

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

ET = TypeVar('ET', bound=Entity)

class Registry(Entity, Generic[ET]):
    """Indexed owning collection with selection and chaining.

    A `Registry` is core's **owning boundary** for intra-related entities.
    It is the canonical dereference mechanism for ID-linked graphs:

    - members are indexed by `uid: UUID`
    - other references should store only UUIDs and dereference through a registry

    ### Selection

    Use `find_one` / `find_all` with a `Selector` for flexible matching.
    Do not overload `get()` with fuzzy identifier logic; `get()` is strictly `UUID → entity`.

    ### Layering

    `chain_find_all` is core's primitive for layered composition:

    - treat multiple registries as a search chain
    - yields matching members across all registries in order

    ### Persistence

    `members` is declared with `Field(exclude=True)` so Pydantic model dumps do not
    automatically include it. `unstructure()` and `structure()` handle member payloads
    explicitly.

    `Registry.unstructure()` includes *all* members as unstructured constructor-form dicts.
    `Registry.structure()` recreates the registry and re-adds structured members.

    ### Duplicate IDs

    `add()` silently overwrites existing members for duplicate `uid` keys.

    ### Dispatch hooks

    Pass `_ctx` to `add`, `get`, or `remove` to allow higher layers to intercept operations.

    `__setitem__` intentionally raises; callers must use `add()` so registry-aware binding
    and dispatch hooks remain consistent.

    See Also
    --------
    `tangl.core.graph.Graph`, `tangl.core.template.TemplateRegistry`

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
        >>> list(Registry.chain_find_all(r, q, selector=s)) == [a, c]
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

    members: dict[UUID, ET] = Field(default_factory=dict, exclude=True)
    # exclude=True just means that structure takes care of it manually, it is
    # still included in unstructured data used by eq_by_content

    def add(self, value: ET, _ctx=None) -> None:
        """Add an entity to the registry.

        Registry-aware values are bound via `bind_registry(self)`. Duplicate UIDs
        overwrite existing entries. When `_ctx` resolves, `do_add_item` may replace
        the inserted item.
        """
        if hasattr(value, "bind_registry"):
            value.bind_registry(self)
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # chance to modify before inserting
            from .dispatch import do_add_item
            value = do_add_item(registry=self, item=value, ctx=_ctx)
        self.members[value.uid] = value

    def remove(self, key: UUID, _ctx=None) -> None:
        """Remove an entity by UUID.

        Missing keys are ignored. Registry-aware values are unbound through
        `bind_registry(None)`. When `_ctx` resolves, `do_remove_item` is invoked
        for post-removal inspection.
        """
        item = self.members.pop(key, None)
        if item is not None and hasattr(item, "bind_registry"):
            item.bind_registry(None)
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # chance to review before discarding
            from .dispatch import do_remove_item
            do_remove_item(registry=self, item=item, ctx=_ctx)
        # or del self.members[key] if you want to throw a key error

    def get(self, key: UUID, _ctx=None) -> Optional[ET]:
        """Return a member by UUID or ``None`` when absent.

        When `_ctx` resolves, `do_get_item` may transform the returned value.
        """
        item = self.members.get(key, None)
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # chance to modify before returning
            from .dispatch import do_get_item
            item = do_get_item(registry=self, item=item, ctx=_ctx)
        return item
        # or return self.members[key] if you want to throw a key error

    def all_labels(self) -> set[str]:
        """Return labels for all stored members."""
        return {value.get_label() for value in self.members.values()}

    @classmethod
    def _filter_and_sort(cls, values, selector=None, sort_key=None) -> Iterator[ET]:
        """Apply optional selector filtering and optional sort ordering."""
        if selector is not None:
            values = selector.filter(values)
        if sort_key is None:
            yield from values
        else:
            yield from sorted(values, key=sort_key)

    @staticmethod
    def _normalize_selector(
        selector: Selector | dict[str, Any] | Any = None,
        **criteria: Any,
    ) -> Selector | None:
        """Normalize v38 selectors and legacy criteria kwargs.

        Compatibility notes
        -------------------
        Legacy callers frequently use:
        - ``find_one(label="foo")``
        - ``find_one(identifier=...)``
        - ``find_one(<identifier>)``

        v38 canonical shape is ``find_one(selector=Selector(...))``.
        This helper accepts both forms.
        """
        if isinstance(selector, dict):
            criteria = {**selector, **criteria}
            selector = None
        elif selector is not None and not isinstance(selector, Selector):
            selector = Selector.from_identifier(selector)

        if selector is None and not criteria:
            return None
        if selector is None:
            return Selector(**criteria)
        if criteria:
            return selector.with_criteria(**criteria)
        return selector

    def find_all(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        sort_key=None,
        **criteria: Any,
    ) -> Iterator[ET]:
        """Yield members matching selector/criteria and optional sort key."""
        selector = self._normalize_selector(selector, **criteria)
        values = self.members.values()
        return self._filter_and_sort(values, selector=selector, sort_key=sort_key)

    def find_one(
        self,
        selector: Selector | dict[str, Any] | Any = None,
        sort_key=None,
        **criteria: Any,
    ) -> Optional[ET]:
        """Return first match from :meth:`find_all`, or ``None``."""
        return next(self.find_all(selector, sort_key=sort_key, **criteria), None)

    @classmethod
    def chain_find_all(
        cls,
        *registries: Self,
        selector: Selector | dict[str, Any] | Any = None,
        sort_key=None,
        **criteria: Any,
    ) -> Iterator[ET]:
        """Yield matches across registries in argument order.

        Use ``next(Registry.chain_find_all(...), None)`` for one-off first-match
        behavior.
        """
        selector = cls._normalize_selector(selector, **criteria)
        values = itertools.chain.from_iterable(r.members.values() for r in registries)
        return cls._filter_and_sort(values, selector=selector, sort_key=sort_key)

    def unstructure(self) -> UnstructuredData:
        """Return constructor-form data including explicitly unstructured members."""
        data = super().unstructure()
        data["members"] = [value.unstructure() for value in self.members.values()]
        return data

    @classmethod
    def structure(cls, data: UnstructuredData, _ctx=None):
        """Structure a registry and re-add structured members."""
        payload = dict(data)
        _members = payload.pop("members", [])
        obj = super().structure(payload, _ctx=_ctx)  # type: Self
        for value in _members:
            obj.add(Entity.structure(value, _ctx=_ctx))
        return obj

    # Provide mapping interface

    def values(self) -> Iterable[ET]:
        """Return registry member values."""
        return self.members.values()

    def keys(self):
        """Legacy mapping alias for member UUID keys."""
        return self.members.keys()

    def items(self):
        """Legacy mapping alias for ``(uid, member)`` pairs."""
        return self.members.items()

    def clear(self) -> None:
        """Remove all members."""
        self.members.clear()

    def __len__(self) -> int:
        return len(self.members)

    def __bool__(self) -> bool:
        return len(self.members) > 0

    def __iter__(self) -> Iterator[ET]:
        # iter values not keys, gets '__contains__(item)' for free
        return iter(self.members.values())

    def __contains__(self, item: Any) -> bool:
        """Support both UUID-key and member-instance containment checks."""
        if isinstance(item, UUID):
            return item in self.members
        if hasattr(item, "uid"):
            return getattr(item, "uid") in self.members
        return item in self.members.values()

    def __getitem__(self, key: UUID):
        return self.get(key)

    def __delitem__(self, key: UUID):
        self.remove(key)

    def __setitem__(self, key, value):
        # refer to add
        raise KeyError(f"May not set items directly by key.  Use `registry.add(item)` instead.")

    def _validate_linkable(self, item: RegistryAware) -> bool:
        """Validate that ``item`` is registry-aware and belongs to this registry."""
        if not isinstance(item, RegistryAware):
            raise TypeError(f"Expected type-bound RegistryAware, got {type(item)}")
        if item.registry is not self:
            raise ValueError("Link item must belong to the same registry")
        if item.uid not in self.members:
            raise ValueError(f"Link item must be added to registry first")
        return True

# Additional bases for entities that can be gathered in a registry

class RegistryAware(Entity):
    """Mixin for entities managed by a single registry.

    Registry-aware entities do not store direct pointers to peer members.
    Instead, they:

    - store UUID references (e.g., `member_ids` in groups)
    - dereference through `self.registry.get(uid)` when needed

    ### Binding contract

    A registry binds itself to an item by calling `item.bind_registry(self)` during `Registry.add()`.
    Registry-aware items should treat the registry reference as an implementation detail:

    - store it as a private attribute (`PrivateAttr`) so pydantic will not copy it
    - raise if rebound to a different registry

    ### Parent convenience

    `parent` is a convenience for hierarchical grouping:

    - it returns the first `HierarchicalGroup` in the owning registry that lists this item
      as a member
    - it is meaningful only when the registry contains hierarchical groups
    - it is cached and must be invalidated when membership changes (`_invalidate_parent_attr`)

    Example:
        >>> a = RegistryAware(); r = Registry(); r.add(a)
        >>> a.registry is r
        True
        >>> Registry().add(a)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        ValueError: Registry is already set ...
        >>> b = RegistryAware(registry=r)
        >>> b.registry is r
        True
        >>> a.registry is b.registry
        True
    """

    _registry: SkipValidation[Registry[RegistryAware]] = PrivateAttr(None)
    # do not want _registry included in unstructuring or copied on creation

    @property
    def registry(self) -> Registry[RegistryAware] | None:
        return self._registry

    def __init__(self, registry=None, graph=None, **kwargs) -> None:
        if registry is None and graph is not None:
            # Compatibility alias: legacy graph items are commonly built with graph=...
            registry = graph
        super().__init__(**kwargs)
        if registry is not None:
            registry.add(self)

    def bind_registry(self, registry: Registry | None) -> None:
        """Bind to a registry pointer or clear binding with ``None``."""
        if registry is None:
            self._registry = None
            return
        if self._registry is not None and (self._registry is not registry):
            raise ValueError(f"Registry is already set {self._registry!r} != {registry!r}")
        self._registry = registry

    @cached_property
    def parent(self) -> Optional[RegistryAware]:
        """Return first owning :class:`HierarchicalGroup`, if present."""
        if self.registry is None:
            return None
        selector = Selector(has_kind=HierarchicalGroup, has_member=self)
        find_one = getattr(self.registry, "find_one")
        try:
            return find_one(selector)
        except TypeError:
            # Legacy registries accept only criteria kwargs.
            return find_one(has_kind=HierarchicalGroup, has_member=self)

    def _invalidate_parent_attr(self):
        # On reparent
        # `parent` is typically a cached_property; pop the cached value directly
        # so property-only compatibility overrides do not raise on `delattr`.
        self.__dict__.pop("parent", None)

RT: TypeAlias = RegistryAware

class EntityGroup(RegistryAware):
    """A registry member that provides a UUID-based view over peer members.

    An `EntityGroup` is itself stored *in* a registry and refers to other members of that
    same registry by UUID.

    - Groups do not own members.
    - Group membership is persisted as `member_ids: list[UUID]`.
    - `members()` dereferences each UUID through the registry.

    This pattern avoids deep nesting during structuring/unstructuring and keeps identity
    and persistence straightforward.

    Example:
        >>> reg = Registry()
        >>> a = RegistryAware(label="abc"); reg.add(a); d = RegistryAware(label="def"); reg.add(d); g = RegistryAware(label="ghi"); reg.add(g)
        >>> e = EntityGroup(); reg.add(e)
        >>> e.add_members(a, d, g)
        >>> list(e.members())
        [<RegistryAware:abc>, <RegistryAware:def>, <RegistryAware:ghi>]
        >>> a = e.member(Selector.from_identifier("abc"))
        >>> assert e.has_member(a)
        >>> e.remove_member(a)
        >>> assert not e.has_member(a)
        >>> assert list(e.members()) == [d, g]
    """
    member_ids: list[UUID] = Field(default_factory=list)

    def member(self, selector: Selector = None, sort_key=None) -> RT:
        """Return first dereferenced member matching optional selector."""
        return next(self.members(selector, sort_key=sort_key), None)

    def members(self, selector: Selector = None, sort_key=None) -> Iterator[RT]:
        """Yield dereferenced members, optionally filtered and sorted."""
        selector = selector or Selector()
        if self.registry is not None:
            items = (item for uid in self.member_ids if (item := self.registry.get(uid)))
            return self.registry._filter_and_sort(items, selector=selector, sort_key=sort_key)
        raise ValueError("Group registry is not set")

    def add_member(self, item: RT) -> None:
        """Add child membership with automatic reparenting."""
        if item is self:
            raise ValueError("Group cannot add itself to itself")
        if self.registry._validate_linkable(item):
            self.member_ids.append(item.uid)

    def add_members(self, *items: RT) -> None:
        """Add multiple members."""
        for item in items:
            self.add_member(item)

    def remove_member(self, item: RT) -> None:
        """Remove child membership and invalidate cached parent."""
        if item is not None and item.uid in self.member_ids:
            self.member_ids.remove(item.uid)

    def has_member(self, item: RT) -> bool:
        """Return membership by UID (delegates to ``__contains__``)."""
        # for selection criteria, uses __contains__ compare-by-uid
        logger.debug(f"{self!r}: checking has_member({item!r}) = {item in self}")
        return item in self

    def __iter__(self) -> Iterator[RegistryAware]:
        # get __contains__ for free
        return iter(self.members())

    def __contains__(self, item: RegistryAware) -> bool:
        # although this is better than iter, b/c it doesn't have to deref id's
        return item.uid in self.member_ids

    def unstructure(self) -> UnstructuredData:
        """Include ``member_ids`` explicitly for stable round-tripping."""
        data = super().unstructure()
        if self.member_ids:
            data["member_ids"] = list(self.member_ids)
        return data

class HierarchicalGroup(EntityGroup):
    """A group that supports parent/child nesting via group membership.

    `HierarchicalGroup` is an `EntityGroup` with an additional convention:

    - a child may belong to **at most one** parent at a time
    - re-parenting is implemented as: remove from old parent → add to new parent

    ### Derived hierarchy properties

    - `parent`: cached lookup of the first `HierarchicalGroup` that lists this group as a member
    - `root`: ascend parents until `None`
    - `ancestors`: `[self, parent, grandparent, ...]`
    - `path`: dotted label path from root (`root.child.grandchild`)

    These are convenience properties intended for scripts and navigation. They rely on
    correct invalidation of the cached `parent` when membership changes.

    Example:
        >>> r = Registry()
        >>> g = HierarchicalGroup(label="g", registry=r)
        >>> h = HierarchicalGroup(label="h", registry=r)
        >>> g.add_child(h)
        >>> assert h.parent is g
        >>> assert h.path == "g.h"
        >>> assert h.ancestors == [h, g]
        >>> g.remove_child(h)
        >>> assert h.parent is None
    """

    # wraps member ops with parent management

    def add_member(self, item: RT) -> None:
        """Add child membership with automatic reparenting."""
        # forces re-parenting, or could throw an exception instead
        logger.debug(f"{self!r}: adding member({item!r})")
        if item.parent is not None:
            # Remove also invalidates item's parent
            item.parent.remove_child(item)
        else:
            # Just invalidate the None parent
            item._invalidate_parent_attr()
        return super().add_member(item)

    def remove_member(self, item: RT) -> None:
        """Remove child membership and invalidate cached parent."""
        if item is not None and item.uid in self.member_ids:
            logger.debug(f"{self!r}: removing member {item!r} from parent {item.parent!r}")
            item._invalidate_parent_attr()
        super().remove_member(item)

    # Aliases for membership ops -> children ops

    def children(self, selector: Selector = None, sort_key=None) -> Iterator[RT]:
        """Alias of :meth:`members` for hierarchy semantics."""
        return self.members(selector=selector, sort_key=sort_key)

    def add_child(self, item: RT):
        self.add_member(item)

    def remove_child(self, item: RT):
        self.remove_member(item)

    @property
    def root(self) -> RT:
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def ancestors(self) -> list[RT]:
        root = self
        result = [self]
        while root.parent is not None:
            root = root.parent
            result.append(root)
        return result

    @property
    def path(self) -> str:
        if self.parent:
            return f"{self.parent.path}.{self.get_label()}"
        return self.get_label()
