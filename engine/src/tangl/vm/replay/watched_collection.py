# tangl/vm/watched_collection.py
from __future__ import annotations
from collections.abc import MutableMapping, MutableSequence, MutableSet
from typing import Any, Iterable

from copy import deepcopy
from .event import EventType

# Event plumbing is provided by WatchedEntityProxy._emit(EventType.UPDATE, name=attr, value=value)
# We keep a tiny shared mixin to normalize "emit an UPDATE with a deep snapshot of current value".

class _Owned:
    __slots__ = ("_owner", "_attr", "_root")

    def __init__(self, owner, attr: str):
        self._owner = owner            # WatchedEntityProxy
        self._attr = attr              # attribute name on the owner entity
        self._root = None  # set by subclasses to the top-level container for this attribute

    def _emit_update(self, snapshot: Any) -> None:
        # Snapshot should be a plain python object (deep copy) so replay is stable.
        self._owner._emit(event_type=EventType.UPDATE,
                          name=self._attr,
                          value=deepcopy(snapshot),
                          old=None)

    # Wrap nested collections returned from __getitem__/get
    def _wrap(self, value):
        if isinstance(value, dict):
            return WatchedDict(self._owner, self._attr, value, root=self._root)
        if isinstance(value, list):
            return WatchedList(self._owner, self._attr, value, root=self._root)
        if isinstance(value, set):
            return WatchedSet(self._owner, self._attr, value, root=self._root)
        return value


class WatchedDict(MutableMapping, _Owned):
    """
    Wraps a dict stored on an entity attribute.
    Emits a single UPDATE(owner, attr, deepcopy(dict)) after each mutating op.
    """
    __slots__ = ("_m", "_root")

    def __init__(self, owner, attr: str, mapping: dict, root: dict | None = None):
        _Owned.__init__(self, owner, attr)
        self._m = mapping
        # Root is the top-level attribute container; nested wrappers share the same root
        self._root = root if root is not None else self._m

    # Core mapping protocol
    def __getitem__(self, k):
        return self._wrap(self._m[k])

    def __setitem__(self, k, v):
        self._m[k] = v
        self._emit_update(self._root)

    def __delitem__(self, k):
        del self._m[k]
        self._emit_update(self._root)

    def __iter__(self):
        return iter(self._m)

    def __len__(self):
        return len(self._m)

    # Convenience & mutators
    def clear(self) -> None:
        self._m.clear()
        self._emit_update(self._root)

    def pop(self, k, *default):
        rv = self._m.pop(k, *default)
        self._emit_update(self._root)
        return rv

    def popitem(self):
        rv = self._m.popitem()
        self._emit_update(self._root)
        return rv

    def setdefault(self, k, default=None):
        if k in self._m:
            return self._wrap(self._m[k])
        inserted = default if default is not None else {}
        self._m[k] = inserted
        self._emit_update(self._root)
        return self._wrap(self._m[k])

    def update(self, other=(), **kw):
        if isinstance(other, dict):
            self._m.update(other, **kw)
        else:
            self._m.update(other, **kw)  # iterable of pairs
        self._emit_update(self._root)

    def __repr__(self):
        return f"WatchedDict({self._attr}={self._m!r})"


class WatchedList(MutableSequence, _Owned):
    """
    Wraps a list stored on an entity attribute.
    Emits an UPDATE(owner, attr, deepcopy(list)) after each mutating op.
    """
    __slots__ = ("_a", "_root")

    def __init__(self, owner, attr: str, array: list, root: list | None = None):
        _Owned.__init__(self, owner, attr)
        self._a = array
        self._root = root if root is not None else self._a

    # Core sequence protocol
    def __getitem__(self, i):
        return self._wrap(self._a[i])

    def __setitem__(self, i, v):
        self._a[i] = v
        self._emit_update(self._root)

    def __delitem__(self, i):
        del self._a[i]
        self._emit_update(self._root)

    def insert(self, i, v) -> None:
        self._a.insert(i, v)
        self._emit_update(self._root)

    def __len__(self):
        return len(self._a)

    # Mutators
    def append(self, v) -> None:
        self._a.append(v)
        self._emit_update(self._root)

    def extend(self, it: Iterable) -> None:
        self._a.extend(it)
        self._emit_update(self._root)

    def remove(self, v) -> None:
        self._a.remove(v)
        self._emit_update(self._root)

    def pop(self, i: int = -1):
        rv = self._a.pop(i)
        self._emit_update(self._root)
        return rv

    def clear(self) -> None:
        self._a.clear()
        self._emit_update(self._root)

    def sort(self, *args, **kwargs) -> None:
        self._a.sort(*args, **kwargs)
        self._emit_update(self._root)

    def reverse(self) -> None:
        self._a.reverse()
        self._emit_update(self._root)

    def __repr__(self):
        return f"WatchedList({self._attr}={self._a!r})"


class WatchedSet(MutableSet, _Owned):
    """
    Wraps a set stored on an entity attribute.
    Emits an UPDATE(owner, attr, deepcopy(set)) after each mutating op.
    """
    __slots__ = ("_s", "_root")

    def __init__(self, owner, attr: str, s: set, root: set | None = None):
        _Owned.__init__(self, owner, attr)
        self._s = s
        self._root = root if root is not None else self._s

    # Core set protocol
    def __contains__(self, x):
        return x in self._s

    def __iter__(self):
        return iter(self._s)

    def __len__(self):
        return len(self._s)

    # Mutators
    def add(self, x) -> None:
        if x not in self._s:
            self._s.add(x)
            self._emit_update(self._root)

    def discard(self, x) -> None:
        if x in self._s:
            self._s.discard(x)
            self._emit_update(self._root)

    def clear(self) -> None:
        if self._s:
            self._s.clear()
            self._emit_update(self._root)

    def update(self, *others: Iterable) -> None:
        changed = False
        for it in others:
            for x in it:
                if x not in self._s:
                    self._s.add(x)
                    changed = True
        if changed:
            self._emit_update(self._root)

    # Immutable ops fall back to built-ins and do NOT emit:
    def __repr__(self):
        return f"WatchedSet({self._attr}={self._s!r})"