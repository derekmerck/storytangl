# tangl/vm/events.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID
from typing import ClassVar, Protocol, Any, Iterable, Optional
from copy import deepcopy

from pydantic import Field, ConfigDict
import wrapt

from tangl.core.entity import Entity
from tangl.core.registry import Registry, VT


class EventType(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

class Event(Entity):
    # Entities b/c they are persisted, structured, unstructured
    model_config: ClassVar = ConfigDict(arbitrary_types_allowed=True)
    source_id: UUID = Field(...)
    event_type: EventType = Field(...)
    name: Optional[str] = None  # attrib name for update
    value: Any = Field(...)
    old_value: Any | None = None

    def apply(self, registry: Registry) -> None:
        if not isinstance(registry, Registry):
            raise TypeError("Event.apply should be called directly on a Registry")
        if self.source_id == registry.uid:
            source = registry
        else:
            source = registry.get(self.source_id)  # type: Entity

        match self.event_type:
            case EventType.CREATE:
                if not isinstance(self.value, Entity):
                    value = Entity.structure(self.value)
                else:
                    value = self.value
                source.add(value)
            case EventType.READ:
                # Non-mutating
                pass
            case EventType.UPDATE:
                setattr(source, self.name, self.value)
            case EventType.DELETE:
                # slightly obtuse, but probably rarely used
                # if it has a _name_ it's a delattr,
                # if it has a _value_, it's a remove item
                if self.name is not None:
                    delattr(source, self.name)
                elif self.value is not None:
                    source.remove(self.value)
                else:
                    raise ValueError("Must have a attrib name or a value-key for remove")

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
        # todo: need to sort events by type, seq so all deletes happen at the end, for example
        # returns an _updated copy_ of the source
        if not isinstance(registry, Registry):
            raise TypeError("Event replay should be called directly on a Registry")
        _registry = deepcopy(registry)
        for event in self.events:
            event.apply(_registry)
        return _registry

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


class WatchedRegistry(WatchedEntityProxy):
    # proxy registry
    __wrapped__: Registry

    def add(self, item: VT) -> None:
        self._emit(event_type=EventType.CREATE,
                   value=item)
        self.__wrapped__.add(item)

    def remove(self, key: UUID) -> None:
        self._emit(event_type=EventType.DELETE, value=key)
        self.__wrapped__.remove(key)

    def get(self, key) -> Optional[WatchedEntityProxy]:
        # wrap retrieved members in a watcher proxy as well
        item = self.__wrapped__.get(key)
        if item is None:
            return None
        proxy = WatchedEntityProxy(wrapped=item, watchers=self._watchers)
        return proxy
