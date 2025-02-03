from __future__ import annotations
from typing import TypeVar, Generic, Callable, Any, Type, Optional
from enum import Enum, auto, IntEnum
import inspect
from itertools import chain
from collections import ChainMap
import logging

from pydantic import Field, ConfigDict

from tangl.utils.dereference_obj_cls import dereference_obj_cls
from .entity import Entity
from .registry import Registry
from .singleton import Singleton

# Type variables
T = TypeVar('T')
EntityT = TypeVar('EntityT', bound=Entity)
ResultT = TypeVar('ResultT')

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class HandlerPriority(IntEnum):
    """Execution priorities for handlers"""
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


class PipelineStrategy(Enum):
    """
    How to process results from multiple handlers.
    None returns are always discarded.

    Modes:
    - 'gather'    : (Default) Collect all results.
    - 'first'     : Return first non-None result.
    - 'pipeline'  : Feed each result into the next callable.
    - 'all_true'  : Return True if all return True.
    - 'any_true'  : Return True if any return True.
    """
    GATHER = auto()        # Default, collect all results
    FIRST = auto()         # Return first non-None result (with early return)
    PIPELINE = auto()      # Pass result through chain
    ALL = auto()           # All must succeed
    ANY = auto()           # Any success is enough (with early return)


class TaskHandler(Entity):
    """
    A callable handler that can be registered with a TaskPipeline for processing Entity instances.

    TaskHandlers maintain metadata about:
    - The function to execute
    - Priority within the pipeline
    - Caller class restrictions
    - Domain specificity
    - Registration order

    The handler can determine if it applies to a given entity based on:
    - Signature compatibility
    - Class hierarchy relationships
    - Domain pattern matching

    Attributes:
        func: The callable to execute
        priority: Execution priority within pipeline
        caller_cls: Optional class restriction for instance methods
        domain: Domain pattern for matching
        registration_order: Monotonic counter for stable ordering
    """
    func: Callable
    priority: HandlerPriority = HandlerPriority.NORMAL
    caller_cls_: Optional[Type[Entity]] = Field(None, alias="caller_cls")
    domain: str = "*"  # global ns
    registration_order: Optional[int] = None

    def __call__(self, *args: Any, **kwargs: Any) -> ResultT:
        return self.func(*args, **kwargs)

    @property
    def caller_cls(self) -> Optional[Type[Entity]]:
        """Computing caller class for instance methods is deferred until the class has been created."""
        if self.caller_cls_ is None:
            if not isinstance(self.func, (classmethod, staticmethod)) and not self.func.__name__ == "<lambda>":
                parts = self.func.__qualname__.split('.')
                if len(parts) < 2:
                    raise ValueError("Cannot get outer scope name for module-level func")
                possible_class_name = parts[-2]  # the thing before .method_name
                logger.debug(f'Parsing {possible_class_name}')
                self.caller_cls_ = dereference_obj_cls(Entity, possible_class_name)
        return self.caller_cls_

    def has_signature(self, *args, **kwargs) -> bool:
        """Test if this method can accept the given arguments."""
        try:
            sig = inspect.signature(self.func)
            sig.bind(*args, **kwargs)
            return True
        except TypeError:
            return False

    def has_caller_cls(self, caller_cls: Type[EntityT]) -> bool:
        """
        Test if this handler's function can be applied to a given entity type.

        Registered staticmethods, classmethods, and lambdas are considered to be
        generally applicable, however, instance methods must be in the mro of the
        calling class.
        """
        if isinstance(self.func, (classmethod, staticmethod)) or self.func.__name__ == "<lambda>":
            return True
        if self.caller_cls:
            return issubclass(caller_cls, self.caller_cls)
        raise ValueError(f"Cannot evaluate {self.func.__qualname__} caller_cls {self.caller_cls} of type {type(self.caller_cls)}")


class TaskPipeline(Singleton, Generic[EntityT, ResultT]):
    """
    A pipeline that processes Entity instances through a series of registered handlers.

    The pipeline maintains an ordered registry of TaskHandlers and executes them according
    to a specified strategy when processing an entity. Handlers are ordered by:

    1. Priority (FIRST through LAST)
    2. Class hierarchy (most specific to most general)
    3. Domain specificity (most specific to most general)
    4. Registration order (maintaining local precedence)

    Results from handlers can be:
    - Gathered into a collection
    - Short-circuited on first result
    - Chained through a processing pipeline
    - Combined with boolean operations

    The pipeline caches handler resolution orders for efficiency but invalidates
    the cache when handlers are registered or unregistered.

    Type Parameters:
        EntityT: The type of entity processed by this pipeline
        ResultT: The type of result produced by handlers

    Attributes:
        pipeline_strategy: How to process and combine handler results
        entity_type: The base entity type for this pipeline
        result_type: The expected result type
        handler_registry: Registry of available handlers
        handler_registrations: Monotonic counter for registration order
    """
    model_config = ConfigDict(frozen=False)

    pipeline_strategy: PipelineStrategy = PipelineStrategy.GATHER
    entity_type: Type[EntityT] = Entity
    result_type: Type[ResultT] = Any

    handler_registry: Registry[TaskHandler] = Field(default_factory=Registry[TaskHandler])
    handler_registrations: int = 0  # can't just use len, b/c we allow unregistering handlers

    _handler_resolution_cache: dict[tuple[type, str], list[TaskHandler]] = {}

    def register(self,
                 priority: HandlerPriority = HandlerPriority.NORMAL,
                 domain: str = "*",
                 caller_cls: type[EntityT] = None):

        def decorator(func: Callable[..., ResultT]):
            handler = TaskHandler(
                func=func,
                priority=priority,
                domain=domain,
                caller_cls=caller_cls,
            )
            self._register_handler(handler)
            return func

        return decorator

    def _invalidate_resolution_cache(self):
        self._resolution_cache = {}

    def _register_handler(self, handler: TaskHandler):
        handler.registration_order = self.handler_registry
        self.handler_registrations += 1
        self.handler_registry.add(handler)
        self._invalidate_resolution_cache()

    def _unregister_handler(self, handler: TaskHandler):
        self.handler_registry.remove(handler)
        # but don't decrement the registration counter
        self._invalidate_resolution_cache()

    def gather_handlers(self, caller_cls: Type[EntityT], domain: str = "*"):
        """
        Computes handler resolution order maintaining:
        1. Priority classes (FIRST->LAST)
        2. Class hierarchy (subclass->superclass)
        3. Domain specificity (specific->general)
        4. Local precedence (later registrations override)
        """
        if cached := self._resolution_cache.get((caller_cls, domain)):
            return cached

        handlers = self.handler_registry.find(caller_cls=caller_cls, domain=domain)

        # Sort by priority maintaining relative ordering within each level
        handlers = sorted(handlers, key=lambda h: (
            h.priority,
            -caller_cls.class_distance(h.caller_cls),
            # -h.domain_specificity(domain),
            # todo: we are just using * fnmatching for now, how are domains represented and dist measured?
            h.registration_order
        ))

        self._resolution_cache[(caller_cls, domain)] = handlers
        return handlers

    def execute(self, entity: EntityT, **context) -> ResultT:
        """Execute the pipeline on a node with given context"""
        handlers = self.gather_handlers(caller_cls=entity.__class__, domain=entity.domain)

        logger.debug(f"{self.label} pipeline handlers to invoke: {(h.func.__name__ for h in handlers)}")

        if not handlers:
            raise ValueError(f"No handlers found for {self.label} with cls {entity.__class__} and domain {entity.domain}")

        match self.pipeline_strategy:

            case PipelineStrategy.GATHER:
                result = [r for h in handlers
                          if (r := h.func(entity, **context)) is not None]

                if not result:
                    return None

                first_type = type(result[0])
                if all( isinstance(r, first_type) for r in result ):
                    if first_type is list:
                        return list(chain(*result))
                    if first_type is set:
                        return set(chain(*result))
                    if first_type is dict:
                        return dict(ChainMap(*result))  # reverse result to put early at the end

                return result

            case PipelineStrategy.FIRST:
                return next((r for h in handlers
                             if (r := h.func(entity, **context)) is not None),
                            None)

            case PipelineStrategy.PIPELINE:
                result = None
                for h in handlers:
                    result = h.func(entity, result, **context)
                return result

            case PipelineStrategy.ALL:
                return all(h.func(entity, **context) for h in handlers)

            case PipelineStrategy.ANY:
                return any(h.func(entity, **context) for h in handlers)

        raise ValueError(f"Unknown strategy: {self.pipeline_strategy}")

