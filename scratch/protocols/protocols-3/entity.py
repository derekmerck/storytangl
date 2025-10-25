"""
Basis for managed entities with registries, components, and handlers.

- Instance and Singleton classes with aliases and self-casting by kwarg
- Handlers that provide extensible MROs and decorators for instance functions without deep inheritance
- Registries for flexibly searchable collections of entities
- Local context management mixins for scoped runtime processing and output
"""
from __future__ import annotations
from typing import Literal, Callable, Protocol, TypeVar, Generic, Union, Iterable, Optional, Self, ClassVar, Any, Type
from pathlib import Path
from uuid import UUID
from enum import IntEnum

from pydantic import BaseModel

from .type_hints import StringSet, StringMap, UniqueString, Identifier

# ---------------
# Entity-related type hints
# ---------------
Tags = StringSet
Context = StringMap       # scoped variable name, value pairs
Criteria = StringMap      # find by tags, attribute values, obj cls, conditions


# ---------------
# TaskHandler
# ---------------
TaskHandlerProcessor = Literal['list', 'first', 'flatten', 'pipeline', 'all', 'any', 'iterator']

class Priority(IntEnum):
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100

class TaskHandlerStrategy(Callable[['Entity', dict], Union[list, dict, bool]]):
    priority: int

class TaskHandler(Protocol):
    """
    TaskHandlers provide an alternate, plugable MRO with some additional features
    like priority handling and runtime modification.

    In general, 'handlers' are collections of class functions, 'managers' are
    instanced handlers that wrap a specific entity and may provide additional state.
    """

    _strategies: dict[UniqueString, set[TaskHandlerStrategy]]  # task_id: { strategies }

    def add_strategy(self, task: Identifier, strategy: TaskHandlerStrategy): ...

    def get_strategies(self, task: Identifier) -> Iterable[TaskHandlerStrategy]: ...

    @classmethod
    def strategy(cls, task: Identifier, priority: int, strategy: TaskHandlerStrategy):
        """Decorator for registering an instance function as a strategy"""

    @classmethod
    def do_task(cls,
                task: Identifier,
                *,
                entity: Entity | Type[Entity],
                processor: TaskHandlerProcessor,
                **kwargs) -> Any:
        """Note this will add a `task(task_id, **kwargs)` wrapper function to every Entity class."""

    @classmethod
    def attach_do_functions(cls, entity_cls: Type[Entity]):
        """This is a metaclass function that will wrap any class functions with the
        'do_' prefix and bind them as instance functions to an entity class that declares
        this handler in _handlers.  It will not override methods that are already declared."""

    @classmethod
    def register_implicit_strategies(cls, entity_cls: Type[Entity]):
        """This is a metaclass function that will search the Entity class MRO for
        sunder methods matching '_on_x' prefix where x matches a handler do-method and
        register the entity method as a strategy for task x."""


# ---------------
# Entity
# ---------------
class EntityCreationHandler(TaskHandler):
    """Called on instance creation, consumes 'obj_cls' initialization kwarg."""

    @TaskHandler.strategy('resolve_class', priority=Priority.FIRST)
    # todo: how do we add this before/while class is being created?
    @classmethod
    def _search_subclasses(cls, obj_cls: Type[Entity] | str) -> Type[Entity]:
        """Checks for named subclass if string argument, tries to resolve string
        kw argument as early as possible."""
        # todo: may want to restrict candidates by domain, so multiple plugins can define
        #       their own 'EntitySubclass' without conflicting?  Domain specific class
        #       resolution handler?

    @classmethod
    def do_resolve_class(cls, obj_cls: Type[Entity] | str = None):
        """Pipelined, so later resolution methods may assume that a subclass name
        has already been resolved to a type if possible."""
        obj_cls = obj_cls or cls
        return super().do_task('resolve_class', obj_cls=obj_cls, processor="pipeline")

    @classmethod
    def do_gather_default_templates(cls, obj_cls: Type[Entity]) -> list[StringMap]:
        ...

    @classmethod
    def do_get_defaults(cls,
                        obj_cls: Type[Entity],
                        *,
                        template_ids: list[str],
                        template_maps: dict[StringMap] = None) -> StringMap:
        template_maps = template_maps or {}
        gathered_maps = cls.do_gather_default_templates(obj_cls)

class EntityMeta(type):
    def __new__(mcs, name, bases, attrs):
        handlers = []
        # Gather handlers respecting MRO order
        for base in reversed(bases):
            handlers.extend(getattr(base, '_handlers', []))
        # Add current class handlers last
        handlers.extend(attrs.get('_handlers', []))
        # Remove duplicates preserving last occurrence
        attrs['_handlers'] = list(dict.fromkeys(handlers))

        cls = super().__new__(mcs, name, bases, attrs)

        # Let handlers do their thing, but don't try to be too clever
        for handler in attrs['_handlers']:
            handler.register_implicit_strategies(cls)
            handler.attach_do_functions(cls)

        return cls

    def __call__(cls, *args,
                 obj_cls: Type | str = None,
                 template_ids: list[str] = None,
                 template_maps: list[StringMap] = None,
                 **kwargs):
        # resolve cls given obj_cls
        obj_cls = obj_cls or cls
        obj_cls = EntityCreationHandler.do_resolve_class(obj_cls)
        # resolve kwargs given templates
        if template_ids is not None:
            default_kwargs = EntityCreationHandler.do_get_defaults(
                obj_cls,
                template_ids=template_ids,
                template_maps=template_maps
            )
            for k, v in default_kwargs.items():
                kwargs.setdefault(k, v)

        return super().__call__(obj_cls, *args, **kwargs)

class MatchHandler(TaskHandler):

    @classmethod
    def do_match_by(cls, entity: Entity, **criteria: Criteria) -> bool:
        """Dispatches various match-by calls depending on criteria x and named
        `_on_match_by_x` sunder functions"""

    @classmethod
    def do_gather_identifiers(cls, entity: Entity) -> set[Identifier]:
        return cls.do_task('gather_identifiers', entity=entity, processor="flatten")

    @classmethod
    def do_gather_tags(cls, entity: Entity) -> Tags:
        return cls.do_task('gather_tags', entity=entity, processor="flatten")

    @classmethod
    def register_implicit_strategies(cls, entity_cls: Type[Entity]):
        """Additionally create new tasks for `on_match_by_x` functions within a class"""


class Entity(Protocol, metaclass=EntityMeta):
    uid: UUID
    label: str
    tags: Tags

    # todo: need to aggregate all handlers from mixin classes, also gets confusing with import order
    _handlers: ClassVar[list[TaskHandler]] = [MatchHandler]

    def _on_gather_identifiers(self) -> list[Identifier]:
        return [self.uid, self.label]

    # Should go directly in handler?
    def _on_match_by_identifier(self, identifier: Identifier) -> bool:
        identifiers = self.gather_identifiers()  # invokes the gather task handler
        return identifier in identifiers

    def _on_gather_tags(self) -> Tags:
        return self.tags

    # Should go directly in handler?
    def _on_match_by_tag(self, tags: Tags) -> bool:
        my_tags = self.gather_tags()  # invokes the gather task handler
        return tags.issubset(my_tags)


# ---------------
# Registry
# ---------------
EVT = TypeVar("EVT", bound=Entity)  # Entity value type

class SearchHandler(Protocol):
    """This is not an entity TaskHandler, but invokes the MatchHandler. Can be used
    directly to filter various collections of entities."""

    @classmethod
    def find_all(cls, entities: Iterable[EVT], **criteria: Criteria) -> Iterable[EVT]:
        """Creates a match-by filter and returns result."""

    @classmethod
    def find_one(cls, entities: Iterable[EVT], **criteria: Criteria) -> EVT: ...


class Registry(dict[Identifier, EVT], Generic[EVT]):

    def add(self, entity: EVT):
        self[entity.uid] = entity

    def __setitem__(self, *args, **kwargs):
        raise NotImplementedError("Use 'add' instead of 'set'")

    def __getitem__(self, key: Identifier) -> Optional[EVT]:
        if x := super().__getitem__(key):
            return x
        return self.find_one(identifier=key)

    def find_all(self, **criteria: Criteria) -> Iterable[EVT]:
        return SearchHandler.find_all(self.values(), **criteria)

    def find_one(self, **criteria: Criteria) -> Optional[EVT]:
        return SearchHandler.find_one(self.values(), **criteria)


# -------------------------
# Singleton Entities
# -------------------------
class Singleton(Entity):
    _instances: ClassVar[Registry[Self]]

    @classmethod
    def get_instance(cls, identifier: Identifier) -> Self:
        return cls._instances.get(identifier)

    @classmethod
    def find_instances(cls, **criteria) -> Iterable[Self]:
        return cls._instances.find_all(**criteria)

    @classmethod
    def find_instance(cls, **criteria) -> Optional[Self]:
        return cls._instances.find_one(**criteria)


SingletonMixin = Singleton

class HasInstanceInheritance(SingletonMixin):
    from_instance: Identifier

class DataSingleton(SingletonMixin):
    # typically media, can defer setting uid until finalized
    data: bin | str = None
    path: Path = None

# -------------------------
# Entity Mixins
# -------------------------
EntityMixin = Entity

class AvailabilityHandler(TaskHandler):

    @classmethod
    def do_lock(cls, entity: Lockable): ...

    @classmethod
    def do_unlock(cls, entity: Lockable): ...

    @classmethod
    def do_available(cls, entity: Lockable) -> bool: ...
    # Conditional extends available with _on_check_satisfied

class Lockable(EntityMixin):
    _handlers: ClassVar[list[Type[TaskHandler]]] = [AvailabilityHandler]
    locked: bool

class ContextHandler(TaskHandler):

    @classmethod
    def do_gather_context(cls, entity: HasContext) -> Context: ...

# Context/Namespace
class HasContext(EntityMixin):
    _handlers: ClassVar[list[Type[TaskHandler]]] = [ContextHandler]
    locals: Context

    def _on_gather_context(self):
        return self.locals

class DonatesContext(HasContext):
    # parent context includes donated tags from children that are outside the cascading scope
    # i.e., a sword asset donates 'has_sword' tag to the holder
    donates_tags: Tags
    donates_locals: Context

    def _on_gather_tags(self) -> Tags:
        return self.donates_tags

    def _on_gather_context(self):
        return self.donates_locals


# Runtime Conditions/Effects
class ConditionHandler(TaskHandler):

    @classmethod
    def eval(cls, expr: str, context: Context) -> Any: ...

    @classmethod
    def do_check_satisfied_for(cls, conditions: list[str], entity: HasContext) -> bool:
        context = entity.gather_context()
        return all( cls.eval(condition, context) for condition in conditions )

    @classmethod
    def do_check_satisfied(cls, entity: HasConditions) -> bool:
        conditions = entity.gather_conditions()
        return cls.do_check_satisfied_for(conditions, entity)

    @classmethod
    def do_gather_conditions(cls, entity: HasConditions) -> bool:
        return super().do_task("gather_conditions", entity=entity, processor="flatten")

class HasConditions(HasContext, EntityMixin):
    _handlers: ClassVar[list[Type[TaskHandler]]] = [ConditionHandler]
    conditions: list[str]

    def _on_gather_conditions(self) -> list[str]:
        return self.conditions

    def _on_available(self) -> bool:
        return self.check_sataisfied()


class EffectHandler(TaskHandler):

    @classmethod
    def exec(cls, expr: str, context: Context) -> Any: ...

    @classmethod
    def do_apply_effects_to(cls, effects: list[str], entity: HasContext):
        context = entity.gather_context()
        for effect in effects:
            cls.exec(effect, context)

    @classmethod
    def do_apply_effects(cls, entity: HasEffects):
        effects = entity.gather_effects(entity)
        cls.do_apply_effects_to(effects, entity)

    @classmethod
    def do_gather_effects(cls, entity: HasEffects) -> list[str]:
        return super().do_task('gather_effects', entity=entity, processor='flatten')

class HasEffects(HasContext, EntityMixin):
    _handlers: ClassVar[list[Type[TaskHandler]]] = [EffectHandler]
    effects: list[str]

    def _on_gather_effects(self) -> list[str]:
        return self.effects

# Renderable Content
class RenderHandler(TaskHandler):
    # Narrative and media handlers extend this
    # Journal calls this
    @classmethod
    def render_str(cls, s: str, context: Context) -> str: ...

    @classmethod
    def do_render_content(cls, entity: Renderable) -> StringMap: ...

class Renderable(HasContext, EntityMixin):
    # Some entities can describe themselves, some can generate media, some can
    # assemble an entire journal entry from children descriptions and media
    _handlers: ClassVar[list[Type[TaskHandler]]] = [RenderHandler]
    text: str
    icon: str

    def _on_render_content(self) -> StringMap: ...
        # something like return k, v for k in [text, icon, label] if getattr(self, k, None)

class TextFragment(BaseModel):
    text: str
    label: str = None
    icon: str = None
