"""
task_pipeline.py

This module provides a flexible and extensible "task handler" system for
processing ``Entity`` objects. It comprises:

- **HandlerPriority**: An IntEnum specifying relative execution order
  (FIRST, EARLY, NORMAL, LATE, LAST).
- **PipelineStrategy**: An Enum detailing how multiple handler results
  should be combined (e.g. gather them all, short-circuit on the first,
  chain them in a pipeline, etc.).
- **TaskHandler**: A callable wrapper (also an Entity) that holds
  metadata about a function's priority, domain, and caller class
  constraints.
- **TaskPipeline**: A Singleton that stores and runs a set of TaskHandlers
  in a particular strategy (GATHER, PIPELINE, FIRST, ALL, ANY, etc.).

Using these components, users can register “hooks” or “handlers”
for specific tasks and execute them in a controlled order on Entities.
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, Any, Type, Optional, Union
from enum import Enum, auto
from itertools import chain
from collections import ChainMap
import functools
import logging

from pydantic import Field, ConfigDict

from tangl.business.core import Entity, Registry, Singleton
from .task_handler import TaskHandler, HandlerPriority

# Type variables
T = TypeVar('T')
EntityT = TypeVar('EntityT', bound=Entity)
ResultT = TypeVar('ResultT')

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class PipelineStrategy(Enum):
    """
    Describes how a pipeline combines or iterates over multiple handler
    results. In all strategies, any handler returning ``None`` is discarded.

    - :attr GATHER:
       Collect results from all handlers in a list (the default).
       Nested lists, sets, or dicts are automatically combined if all
       returned items share the same type.
    - :attr PIPELINE:
       Treat each handler's return as the input to the next handler,
       like a functional pipeline.
    - :attr ITER:
       Return a generator of partial calls for each handler, allowing
       manual iteration or delayed execution.
    - :attr FIRST:
       Return only the first non-``None`` handler result, short-circuiting
       immediately thereafter.
    - :attr ALL:
       Return a boolean indicating whether *all* handlers returned a truthy
       value, short-circuiting on the first falsy result.
    - :attr ANY:
       Return a boolean indicating whether *any* handler returned a truthy
       value, short-circuiting on the first True result.
    """
    GATHER = auto()     # Default, process and collect all results
    PIPELINE = auto()   # Pass result through chain
    ITER = auto()       # Return a generator of partial funcs for each handler call
    FIRST = auto()      # Return first non-None result (with early return)
    ALL = auto()        # All must succeed (with early return)
    ANY = auto()        # Any success is enough (with early return)


class TaskPipeline(Singleton, Generic[EntityT, ResultT]):
    """
    A specialized pipeline that processes :class:`~tangl.core.Entity`
    objects through a collection of :class:`TaskHandler` callbacks,
    arranged according to priority, domain, and class specificity.

    **Ordering**:
      1. :class:`HandlerPriority` (lowest number first).
      2. Class hierarchy (most derived to most base).
      3. Domain specificity (not yet fully implemented, but intended
         to prefer narrower patterns over ``"*"``).
      4. Registration order (the order in which handlers are added,
         ensuring stable tie-breaking).

    **Strategies**:
      Defined by :class:`PipelineStrategy`, controlling whether you
      gather all results, chain them, short-circuit, etc.

    **Caching**:
      Handler resolution is cached in :attr:`_resolution_cache`
      for performance. Any time a handler is added/removed, the cache
      is invalidated.

    :param pipeline_strategy: Defines how multiple handler results are
                              processed or combined. Defaults to
                              :attr:`~PipelineStrategy.GATHER`.
    :type pipeline_strategy: PipelineStrategy
    :param entity_type: The :class:`Entity` subtype this pipeline
                        primarily processes.
    :type entity_type: Type[EntityT]
    :param result_type: The expected result type (for type hinting).
    :type result_type: Type[ResultT]
    :param handler_registry: Where :class:`TaskHandler` objects are stored.
    :type handler_registry: Registry[TaskHandler]
    :param handler_registrations: Monotonically increasing counter
                                  to track registration order.
    :type handler_registrations: int
    """
    model_config = ConfigDict(frozen=False)

    pipeline_strategy: PipelineStrategy = PipelineStrategy.GATHER
    entity_type: Type[EntityT] = Entity
    result_type: Type[ResultT] = Any

    handler_registry: Registry[TaskHandler] = Field(default_factory=Registry[TaskHandler])
    handler_registrations: int = 0  # can't just use len, b/c we allow unregistering handlers

    _resolution_cache: dict[tuple[type, str], list[TaskHandler]] = {}

    def register(self,
                 priority: HandlerPriority = HandlerPriority.NORMAL,
                 domain: str = "*",
                 caller_cls: type[EntityT] = None):
        """
        Decorator to register a new handler with this pipeline.

        :param priority: The execution priority, defaults to NORMAL.
        :type priority: HandlerPriority
        :param domain: A domain pattern restricting which entities are
                       handled (default ``"*"``).
        :type domain: str
        :param caller_cls: Class restriction for instance methods; if
                           None, it may be inferred later.
        :type caller_cls: type[EntityT]
        :return: A function decorator that registers the wrapped function
                 as a :class:`TaskHandler`.
        :rtype: Callable[[Callable[..., ResultT]], Callable[..., ResultT]]

        Example::
          >>> pipeline = TaskPipeline()
          >>> @pipeline.register(priority=HandlerPriority.FIRST)
          >>> def my_handler(entity, **context):
          >>>    ...
          >>>    return some_value
        """
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
        """
        Internal method that clears the cached handler resolution
        whenever a handler is added or removed.
        """
        self._resolution_cache = {}

    def _register_handler(self, handler: TaskHandler):
        """
        Internal helper to place a handler in the registry, increment
        the registration count, and invalidate caches.
        """
        handler.registration_order = self.handler_registrations
        self.handler_registrations += 1
        self.handler_registry.add(handler)
        self._invalidate_resolution_cache()

    def _unregister_handler(self, handler: TaskHandler):
        """
        Remove a handler from the registry and invalidate caches. The
        monotonic registration counter is not decremented.
        """
        self.handler_registry.remove(handler)
        # but don't decrement the registration counter
        self._invalidate_resolution_cache()

    def gather_handlers(self,
                        caller_cls: Type[EntityT],
                        domain: str = "*",
                        extra_handlers: list[Callable] = None):
        """
        Retrieve handlers applicable to a given ``caller_cls`` and
        ``domain``, in final sorted order.

        Sorting order:
          1) :attr:`TaskHandler.priority` (ascending)
          2) Class hierarchy distance (more derived classes first)
          3) Domain specificity (TODO: not fully implemented)
          4) :attr:`TaskHandler.registration_order`

        :param caller_cls: The class of the entity being processed.
        :type caller_cls: Type[EntityT]
        :param domain: The entity's domain, defaults to ``"*"``.
        :type domain: str
        :param extra_handlers: Additional handlers to inject into the
               pipeline for this invocation only
        :type extra_handlers: list[TaskHandler|Callable]
        :return: A list of all matching handlers in sorted order.
        :rtype: list[TaskHandler]
        """

        def _sort_handlers(_handlers: list[TaskHandler]) -> list[TaskHandler]:
            # Sort by priority maintaining relative ordering within each level
            return sorted(_handlers, key=lambda h: (
                h.priority,
                -caller_cls.class_distance(h.caller_cls),
                # calling entity should be a subclass of h.caller_class
                # -h.domain_specificity(domain),
                # todo: we are just using * fnmatch for now, how are domains represented and dist measured?
                h.registration_order
            ))

        if (caller_cls, domain) in self._resolution_cache:
            handlers = self._resolution_cache.get((caller_cls, domain))
        else:
            handlers = self.handler_registry.find(caller_cls=caller_cls, domain=domain)
            handlers = _sort_handlers(handlers)
            self._resolution_cache[(caller_cls, domain)] = handlers

        if extra_handlers:
            # Note: work on a copy of handlers here, or else you will update
            #       the mutable list entry in the cache
            handlers = list(handlers)
            for i, h in enumerate(extra_handlers):
                if isinstance(h, TaskHandler):
                    if h.has_caller_cls(caller_cls) and h.has_domain(domain):
                        logger.debug(f"Allowing {h.func.__name__} for {caller_cls.__name__}")
                        h.registration_order = self.handler_registrations + i
                        handlers.append(h)
                elif isinstance(h, Callable):
                    # Cast to TaskHandler if they are bare Callables,
                    h = TaskHandler(func=h, registration_order=self.handler_registrations + i)
                    handlers.append(h)
                else:
                    raise TypeError('Extra handlers must be a callable or TaskHandler')
            handlers = _sort_handlers(handlers)

        return handlers

    def execute(self, entity: EntityT, extra_handlers: list[Callable] = None, **context) -> ResultT:
        """
        Execute all applicable handlers for a given entity, combining
        results according to :attr:`pipeline_strategy`.

        :param entity: The entity to be processed by the pipeline.
        :type entity: EntityT
        :param context: Additional keyword arguments to pass to each handler.
        :return: The result of combining handler outputs (may be None,
                 a list, a boolean, etc., depending on the strategy).
        :param extra_handlers: Additional handlers to inject into the
                 pipeline for this invocation only
        :type extra_handlers: list[TaskHandler|Callable]
        :rtype: ResultT
        :raises ValueError: If no handlers are found for the entity.
        """
        handlers = self.gather_handlers(
            caller_cls=entity.__class__,
            domain=entity.domain,
            extra_handlers=extra_handlers)

        logger.debug(f"{self.label} pipeline handlers to invoke: {[h.registration_order for h in handlers]}")

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

            case PipelineStrategy.PIPELINE:
                result = None
                for h in handlers:
                    result = h.func(entity, result, **context)
                return result

            case PipelineStrategy.ITER:
                return (functools.partial(h.func, entity, **context) for h in handlers)

            case PipelineStrategy.FIRST:
                return next((r for h in handlers
                             if (r := h.func(entity, **context)) is not None),
                            None)

            case PipelineStrategy.ALL:
                return all(h.func(entity, **context) for h in handlers)

            case PipelineStrategy.ANY:
                return any(h.func(entity, **context) for h in handlers)

        raise ValueError(f"Unknown strategy: {self.pipeline_strategy}")
