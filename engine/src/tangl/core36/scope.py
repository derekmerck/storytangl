from __future__ import annotations
from uuid import UUID
from typing import Any, Callable, Iterator, Type, NewType, Self, Protocol
from dataclasses import dataclass, field

from tangl.type_hints import Label, StringMap, Identifier
from .entity import Entity, Registry, SingletonEntity

# A scope is an entity with Domains, State, Shape, Behaviors
class Scope(Protocol):
    """
    Entities that want to participate in a scope may include 4 orthogonal
    capabilities: domains, state, shape, and behaviors

    Domains are used to push opt-in scopes onto the scope stack.

    State and shape cascade according to scope ordering in the context, and
    the context exposes the current chainmap of state and shape identifiers as
    `context.namespace`.

    Behaviors cascade with other behavior layers and return chains of matching
    behaviors for a phase and entity.
    """
    # r/o
    def iter_domains(self) -> Iterator[Domain]: ...
    def get_value(self, key: str) -> Any: ...
    def find_behaviors_for(self, service: ServiceName, entity: Entity, ns: StringMap) -> Iterator[Behavior]: ...
    def get_element(self, key: Identifier) -> HasShape: ... # Only structural scopes
    def find_elements(self, **criteria: Any) -> Iterator[HasShape]: ...  # Only structural scopes

    # r/w
    def set_value(self, key: str, value: Any): ...
    def add_behavior(self, behavior: Behavior): ...  # Only instance domains
    def add_element(self, shape: HasShape): ...      # Only structural scopes
    def remove_element(self, key: HasShape | Identifier): ... # Only structural scopes

# ----- SCOPE MIXINS ------------

@dataclass
class HasDomains:
    # opt-in domains that this entity subscribes to
    domains: list[Scope] = field(default_factory=list)

    def iter_domains(self) -> Iterator[Scope]:
        yield from self.domains


@dataclass
class HasState:
    # Do serialize, these are locals
    state: dict[str, Any] = field(default_factory=dict)

    # State registry accessors

    def get_value(self, key: str) -> Any:
        return self.state.get(key)
    def set_value(self, key: str, value: Any):
        self.state[key] = value


ServiceName = NewType("ServiceName", str)

@dataclass
class Behavior(Entity):
    service: ServiceName = None
    caller_cls: Type[Entity] = Entity
    priority: int = -1
    func: Callable[[Entity, dict[str, Any]], bool] = None

class BehaviorRegistry(Registry[Behavior]):
    def find_for(self, service: ServiceName, entity, ns: dict = None) -> Iterator[Behavior]:
        raise NotImplementedError()

    def register(self, service: ServiceName, priority: int = None):
        def dec(func: Callable[[Entity, dict], Any]):
            b = Behavior(func=func, service=service, priority=priority)
            self.add(b)
        return dec

@dataclass
class HasBehaviors:
    # Required, but do not create or serialize, include from framework code when structuring
    behaviors: BehaviorRegistry = field(kw_only=True)

    # Behavior registry accessors

    def find_behaviors_for(self, service: ServiceName, entity: Entity, ns: dict) -> Iterator[Behavior]:
        return self.behaviors.find_for(service=service, entity=entity, ns=ns)



class ShapeRegistry(Registry['HasShape']):

    def add(self, item: HasShape):
        item.shape_registry = self
        if item not in item.shape_registry:
            super().add(item)

@dataclass
class HasShape(Entity):
    # Required, but do not create or serialize, include from framework code when structuring
    shape_registry: ShapeRegistry = field(kw_only=True)

    # Shape registry accessors

    def get_element(self, key: UUID) -> Self:
        return self.shape_registry.get(key)

    def find_elements(self, **criteria) -> Iterator[Self]:
        return self.shape_registry.find(**criteria)


# ----- BASIC SCOPE OBJECTS ------------

class Domain(HasDomains, HasState, HasBehaviors, SingletonEntity):
    """
    Domains are opt-in scopes. Membership is declared.
    """
    # Domains may register instance behaviors since they are immortal, but nothing
    # else should, so the behavior registries don't reference ephemeral nodes.
    behaviors: BehaviorRegistry = field(default_factory=BehaviorRegistry)

    def add_behavior(self, behavior: Behavior):
        self.behaviors.add(behavior)

    def remove_behavior(self, behavior: Behavior | UUID):
        self.behaviors.remove(behavior)

PATH_SEP = "/"

class StructuralScope(HasDomains, HasState, HasBehaviors, HasShape, Entity):

    parent_id: UUID = None

    @property
    def parent(self):
        if self.parent_id:
            return self.get_element(self.parent_id)

    @parent.setter
    def parent(self, el: Self | UUID):
        if isinstance(el, UUID):
            if el not in self.shape_registry:
                raise ValueError(f"Cannot set with unregistered UUID: {el}")
            el_id = el
        elif isinstance(el, HasShape):
            self.shape_registry.add(el)
            el_id = el.uid
        else:
            raise TypeError(f"Expected UUID or Node, got {type(el)}")
        self.parent_id = el_id

    def ancestors(self) -> Iterator[Self]:
        root = self
        while root:
            yield root
            root = root.parent

    @property
    def path(self):
        parts = [ a.label for a in self.ancestors() ]
        return PATH_SEP.join(parts)

    def iter_domains(self) -> Iterator[Scope]:
        # Walk ancestor tree
        yield from super().iter_domains()
        if self.parent_id and hasattr(self.parent, 'iter_domains'):
            yield from self.parent.iter_domains()

    # shape registry has the complete graph, elements is this object's subgraph
    element_ids: list[UUID] = field(default_factory=list)

    def add_element(self, el: Self):
        el.parent = self
        self.shape_registry.add(el)
        if el.uid not in self.element_ids:
            self.element_ids.append(el.uid)

    def remove_element(self, el: Self | UUID, discard: bool = False):
        if isinstance(el, UUID):
            el_id = el
        elif isinstance(el, Entity):
            el_id = el.uid
        else:
            raise TypeError(f"Expected UUID, Node, or Edge, but got {type(el)}")
        if el_id in self.element_ids:
            self.element_ids.remove(el_id)
        if discard:
            self.shape_registry.remove(el)

    # Convenience

    @property
    def elements(self) -> list[HasShape]:
        return [ self.get_element(el_id) for el_id in self.element_ids ]

