# tangl/vm/watched_proxy
"""
Proxies that watch entity/registry mutations and emit replayable events.
"""
from dataclasses import dataclass, field
from typing import Optional, Iterable, Any
from uuid import UUID

import wrapt

from typing import Protocol

from tangl.core import Entity, Registry, GraphItem
from .event import Event, EventType
from .watched_collection import WatchedSet, WatchedDict, WatchedList


class EventWatcher(Protocol):
    """Protocol for event sinks that accept :class:`~tangl.vm.replay.event.Event`."""
    def submit(self, event: Event) -> None: ...

class PrintWatcher:
    """
    Trivial watcher that prints each event (for debugging).
    """
    @staticmethod
    def submit(event: Event) -> None:
        print(event)

# dataclass for simplified init, not serialized or tracked
@dataclass
class ReplayWatcher:
    """
    Buffer of emitted events with helpers to canonicalize, replay, and clear.

    Why
    ----
    Useful in tests and preview execution to collect mutations before deciding to
    commit; replay is performed against a copy of a registry.

    Key Features
    ------------
    * **Append-only buffer** – :attr:`events` in emission order.
    * **Canonicalize+replay** – :meth:`replay` collapses redundant updates before applying.
    * **Reset** – :meth:`clear` empties the buffer.
    """
    events: list[Event] = field(default_factory=list)
    def submit(self, event: Event) -> None:
        self.events.append(event)

    def replay(self, registry: Registry) -> Registry:
        """Apply buffered events to a deep copy of `registry` and return it."""
        return Event.apply_all(Event.canonicalize_events(self.events), registry)

    def clear(self) -> None:
        self.events = []


class WatchedEntityProxy(wrapt.ObjectProxy):
    """
    Proxy that observes attribute mutations on an :class:`~tangl.core.Entity`.

    Why
    ----
    Intercepts ``setattr``/``delattr`` and emits typed events so changes can be
    journaled and replayed. Wraps mutable attributes (dict/list/set) with watched
    variants to observe in-place edits.

    Key Features
    ------------
    * **Attribute interception** – emits UPDATE/DELETE for field changes.
    * **Deep watching** – wraps dict/list/set values as :class:`WatchedDict`, :class:`WatchedList`, :class:`WatchedSet`.
    * **Entity-aware values** – values/olds that are :class:`~tangl.core.Entity` are unstructured in events.
    * **Composable** – multiple watchers may be attached.

    API
    ---
    - :meth:`attach_watchers` – add watchers dynamically.
    - :meth:`__setattr__` / :meth:`__delattr__` – emit events on mutation.
    - :meth:`__getattr__` – returns wrapped collections for deep watching.

    Notes
    -----
    Attributes holding *non-graph* entities are not auto-wrapped yet; consider
    wrapping them explicitly if you need deep observation.
    """
    _watchers: list[EventWatcher]
    __wrapped__: Entity

    def __init__(self,
                 wrapped: Entity,
                 watchers: Optional[Iterable[EventWatcher]] = None) -> None:
        super().__init__(wrapped)
        # Keep proxy state in __dict__ (not forwarded to wrapped)
        self.__dict__['_watchers'] = list(watchers or [])

    def _emit(self, *, event_type: EventType, value: Any, name: str = None, old: Any = None):
        source = self.__wrapped__
        if isinstance(value, Entity):
            value = value.unstructure()
        if isinstance(old, Entity):
            old = old.unstructure()
        event = Event(
            source_id=source.uid,
            event_type=event_type,
            name=name,
            value=value,
            old_value=old,
        )
        for w in self._watchers:
            w.submit(event)

    # Intercept attribute sets on the *wrapped object*
    def __setattr__(self, name: str, value: Any) -> None:
        # allow proxy internals to be set normally
        if name in ("_watchers", "__wrapped__", "_self_wrapper__"):
            return super().__setattr__(name, value)

        # read old value from wrapped (if present)
        try:
            old = getattr(self.__wrapped__, name)
        except AttributeError:
            old = None

        # set on the wrapped object
        setattr(self.__wrapped__, name, value)

        # emit after mutation
        self._emit(event_type=EventType.UPDATE, name=name, value=value, old=old)

    # Intercept attribute deletes on the *wrapped object*
    def __delattr__(self, name: str) -> None:
        # allow proxy internals to be deleted normally
        if name in ("_watchers", "__wrapped__", "_self_wrapper__"):
            return super().__delattr__(name)

        # read old value from wrapped (if present)
        try:
            old = getattr(self.__wrapped__, name)
        except AttributeError:
            old = None

        # delete on the wrapped object
        delattr(self.__wrapped__, name)

        # emit after mutation
        self._emit(event_type=EventType.DELETE, name=name, value=None, old=old)

    def attach_watchers(self, auditors: Iterable[EventWatcher]) -> None:
        self._watchers.extend(auditors)

    def _wrap_value(self, name: str, value):
        # wrap mutable builtins so we can observe in-place mutations
        if isinstance(value, dict):
            return WatchedDict(self, name, value)
        if isinstance(value, list):
            return WatchedList(self, name, value)
        if isinstance(value, set):
            return WatchedSet(self, name, value)

        # NOTE: Attributes that directly hold a non-graph Entity (e.g., a Record) are not
        # auto-wrapped via registry.get(). If deep observation is required, consider:
        # if isinstance(value, Entity) and not isinstance(value, GraphItem):
        #     return WatchedEntityProxy(wrapped=value, watchers=self._watchers)
        return value

    def __getattr__(self, name: str):
        # proxy internals
        if name in ("_watchers", "__wrapped__", "_self_wrapper__", "_wrap_value", "_emit", "EventType"):
            return super().__getattr__(name)
        value = getattr(self.__wrapped__, name)
        return self._wrap_value(name, value)



class WatchedRegistry(WatchedEntityProxy):
    """
    Registry proxy that emits CREATE/DELETE on membership changes and returns watched items.

    Why
    ----
    Bridges registry-level CRUD to the event stream and ensures fetched members
    are proxied for deep observation.

    Key Features
    ------------
    * **CREATE/DELETE events** – emitted by :meth:`add` and :meth:`remove`.
    * **Watched retrieval** – :meth:`get` returns :class:`WatchedEntityProxy` for items.

    API
    ---
    - :meth:`add(item)` – emit CREATE then delegate.
    - :meth:`remove(key)` – emit DELETE then delegate.
    - :meth:`get(key)` – return a watched proxy or ``None``.
    """
    # proxy registry
    __wrapped__: Registry

    def add(self, item) -> None:
        self._emit(event_type=EventType.CREATE,
                   value=item)
        self.__wrapped__.add(item)

    def remove(self, key: UUID) -> None:
        self._emit(event_type=EventType.DELETE, value=key)
        self.__wrapped__.remove(key)

    def get(self, key) -> Optional[WatchedEntityProxy]:
        # This covers property accessors and collections of graph items automatically.
        # Singletons and handlers are not covered, but they are not part of the graph state.
        # Nodes that hold a non-graph entity in an attribute would not be discovered
        # this way though.
        item = self.__wrapped__.get(key)
        if item is None:
            return None
        proxy = WatchedEntityProxy(wrapped=item, watchers=self._watchers)
        return proxy
