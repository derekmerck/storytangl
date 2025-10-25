from typing import Callable, Literal, Any, Iterator
from dataclasses import dataclass, field
from uuid import UUID

from tangl.type_hints import StringMap
from .entity import Entity
from .scope import BehaviorRegistry
from .graph import Node, Edge, ChoiceEdge, Traversable

# Behaviors

ServiceName = Literal[
    'PREDICATE',      # Compile predicates for dependencies
    'PROVISION',      # Create dependencies and attach affordances
    'PREREQUISITE',   # Check for automatic redirect choice
    'UPDATE',         # Mutate state
    'RENDER',         # Create fragments
    'COMPOSITE',      # Compose journal entry fro fragment groups and ladders
    'FINALIZE',       # Mutate state post-rendering, consume resources, etc.
    'POSTREQUISITE',  # Check for automatic after choice
]

behaviors = BehaviorRegistry()

# ----- PREDICATES --------------

@dataclass
class HasPredicate(Entity):
    predicate: list[Callable[[Entity, StringMap], bool]] = lambda e, ns: True

    @behaviors.register(service="PREDICATE")
    def predicate_satisfied(self, ns: StringMap) -> bool:
        for predicate in self.predicate:
            if predicate(self, ns) is False:
                return False
        return True


# ------ PROVISIONING ------------

class HasRequirements(Edge):
    requirements: dict[str, Any] = field(default_factory=dict)
    provider_id: UUID = None
    @property
    def provider(self):
        return self.get_element(self.provider_id)
    @provider.setter
    def provider(self, provider: Entity):
        self.provider_id = provider.uid

    @behaviors.register(service="PROVISION")
    def find_providers(self, ns: dict) -> Iterator[Entity]:
        ...

@dataclass
class Dependency(HasRequirements):
    successor_id: type(None) = None
    @property
    def successor(self):
        return self.provider

@dataclass
class Affordance(HasRequirements):
    predecessor_id: type(None) = None
    @property
    def predecessor(self):
        return self.provider


# ----- EFFECTS -------------------

@dataclass
class HasTraversalEffects(Node):
    # Entry effects and bookkeeping/finalize effects
    effects: list[Callable[[Entity, StringMap], bool]] = lambda e, ns: True

    @behaviors.register(service="UPDATE")
    def apply_update_effects(self, ns: StringMap):
        for effect in self.effects:
            effect(self, ns)

    @behaviors.register(service="FINALIZE")
    def apply_finalize_effects(self, ns: StringMap):
        ...


# ----- CHOICES --------------------

@dataclass
class HasChoices(Traversable):

    @behaviors.register(service="PREREQUISITE")
    def _get_prereq_choice(self, ns: StringMap) -> ChoiceEdge | None:
        ...

    @behaviors.register(service="POSTREQUISITE")
    def _get_postreq_choice(self, ns: StringMap) -> ChoiceEdge | None:
        ...

    def get_choices(self) -> list[ChoiceEdge]:
        ...


# ----- RENDERABLE ----------------

@dataclass
class Fragment(Entity):
    fragment_type: str = None
    content: str = None

@dataclass
class Renderable(Node):
    content: Any = None

    @behaviors.register(service="RENDER")
    def _render_content(self, ns: dict) -> Fragment | list[Fragment]:
        return Fragment(content=self.content)

    @behaviors.register(service="COMPOSITE")
    def _compose_fragments(self, ns: dict) -> list[Fragment]:
        # Use a fragment sink then transfer to the journal?
        ...
