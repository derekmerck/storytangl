# tangl/vm/replay/watched_proxy.py
from dataclasses import dataclass, field
from typing import Optional, Iterable, Any
from uuid import UUID

import wrapt

from typing import Protocol

from tangl.core import Entity, Registry
from .events import Event, EventType
from .wrapped_collection import WatchedSet, WatchedDict, WatchedList


class EventWatcher(Protocol):
    def submit(self, event: Event) -> None: ...

class PrintWatcher:
    @staticmethod
    def submit(event: Event) -> None:
        print(event)

# dataclass for simplified init, not serialized or tracked
@dataclass
class ReplayWatcher:
    events: list[Event] = field(default_factory=list)
    def submit(self, event: Event) -> None:
        self.events.append(event)

    def replay(self, registry: Registry) -> Registry:
        """Apply buffered events to a deep copy of `registry` and return it."""
        return Event.apply_all(Event.canonicalize_events(self.events), registry)

    def clear(self) -> None:
        self.events = []


class WatchedEntityProxy(wrapt.ObjectProxy):
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
        return value

    def __getattr__(self, name: str):
        # proxy internals
        if name in ("_watchers", "__wrapped__", "_self_wrapper__", "_wrap_value", "_emit", "EventType"):
            return super().__getattr__(name)
        value = getattr(self.__wrapped__, name)
        return self._wrap_value(name, value)

    # todo: need to provide a wrapped collection proxy if getattr returns a
    #       mutable collection like 'locals', collections need to know to return a
    #       further wrapped object (entity or collection) if necessary

    # todo: attributes that directly hold a non-graph entity like a Record will
    #       not get wrapped via graph.get(), so we need to check for that as well.


class WatchedRegistry(WatchedEntityProxy):
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
