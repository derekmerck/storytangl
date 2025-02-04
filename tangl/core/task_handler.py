"""
handler.py

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
from typing import TypeVar, Generic, Callable, Any, Type, Optional
from enum import Enum, auto, IntEnum
import inspect
from itertools import chain
from collections import ChainMap
import functools
import logging

from pydantic import Field, ConfigDict

from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.core.entity import Entity, Registry, Singleton

# Type variables
T = TypeVar('T')
EntityT = TypeVar('EntityT', bound=Entity)
ResultT = TypeVar('ResultT')

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class HandlerPriority(IntEnum):
    """
    Execution priorities for handlers.

    Each TaskHandler is assigned a priority to control high-level ordering.
    The pipeline sorts handlers by these priorities first, with the
    following semantics:

    - :attr:`FIRST` (0) – Runs before all other handlers.
    - :attr:`EARLY` (25) – Runs after FIRST, but before NORMAL.
    - :attr:`NORMAL` (50) – Default middle priority.
    - :attr:`LATE` (75) – Runs after NORMAL, before LAST.
    - :attr:`LAST` (100) – Runs very last in the sequence.

    Users are also free to use any int as a priority. Values lower than 0 will
    run before FIRST, greater than 100 will run after LAST, and other values will
    sort as expected.
    """
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


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


class TaskHandler(Entity):
    """
    A wrapper around a callable that can be registered with a
    :class:`TaskPipeline` for processing :class:`~tangl.core.Entity`
    instances. This class also extends :class:`~tangl.core.Entity`,
    letting it participate in broader Tangl logic (e.g., domain-based
    filtering, hashing, serialization).

    **Key Features**:

    - **Function Binding**: A Python callable (instance, class, or static
      method, or even a lambda).
    - **Priority**: An enumerated level for coarse-grained ordering among
      handlers.
    - **Domain**: A pattern (usually wildcard by default) to further
      restrict applicability.
    - **Caller Class**: An optional class restriction so that instance
      methods only apply when the calling entity is a subclass.

    :param func: The underlying callable to be invoked.
    :type func: Callable
    :param priority: High-level ordering in the pipeline.
    :type priority: HandlerPriority
    :param caller_cls_: The class restriction, if any, for instance methods.
                       If None, it may be auto-inferred from ``func.__qualname__``.
    :type caller_cls_: Optional[Type[Entity]]
    :param domain: A domain pattern (e.g. ``"mydomain.*"``) for matching
                   an entity's domain.
    :type domain: str
    :param registration_order: A monotonic counter that ensures stable sorting
                               when priorities are the same.
    :type registration_order: Optional[int]
    """
    func: Callable
    priority: HandlerPriority = HandlerPriority.NORMAL
    caller_cls_: Optional[Type[Entity]] = Field(None, alias="caller_cls")
    domain: str = "*"  # global ns
    registration_order: Optional[int] = None

    def __call__(self, *args: Any, **kwargs: Any) -> ResultT:
        """
        Invoke the underlying callable with the provided args/kwargs.

        :return: The callable's return value.
        :rtype: ResultT
        """
        return self.func(*args, **kwargs)

    @property
    def caller_cls(self) -> Optional[Type[Entity]]:
        """
        Lazily determine the actual class that owns this handler
        if it was not explicitly specified at creation time.

        Instance methods, for example, can be inferred by parsing
        ``func.__qualname__`` to get the immediate parent class name,
        then dereferencing that name in the Tangl entity hierarchy.

        :return: The class object representing the method's owner, or None
                 if it's a staticmethod/lambda.
        :rtype: Optional[Type[Entity]]
        """
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
        """
        Check whether this function can be invoked with the given signature.

        Useful if your pipeline is passing arguments that might vary
        in shape or number.

        :return: True if the function's signature can bind to the arguments.
        :rtype: bool
        """
        try:
            sig = inspect.signature(self.func)
            sig.bind(*args, **kwargs)
            return True
        except TypeError:
            return False

    def has_caller_cls(self, caller_cls: Type[EntityT]) -> bool:
        """
        Determine if this handler can apply to the given ``caller_cls``
        based on class hierarchy.

        - If ``self.func`` is a classmethod, staticmethod, or lambda,
          it's considered globally applicable.
        - Otherwise, we check that the pipeline's ``caller_cls`` is a
          subclass of the declared or inferred ``self.caller_cls``.

        :param caller_cls: The class of the entity being processed.
        :type caller_cls: Type[EntityT]
        :return: True if it should apply, False otherwise.
        :rtype: bool
        :raises ValueError: If we cannot evaluate or infer the
                            handler's ``caller_cls``.
        """
        if isinstance(self.func, (classmethod, staticmethod)) or self.func.__name__ == "<lambda>":
            return True
        if self.caller_cls:
            return issubclass(caller_cls, self.caller_cls)
        raise ValueError(f"Cannot evaluate {self.func.__qualname__} caller_cls {self.caller_cls} of type {type(self.caller_cls)}")


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
      Handler resolution is cached in :attr:`_handler_resolution_cache`
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

    _handler_resolution_cache: dict[tuple[type, str], list[TaskHandler]] = {}

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
        handler.registration_order = self.handler_registry
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

    def gather_handlers(self, caller_cls: Type[EntityT], domain: str = "*"):
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
        :return: A list of all matching handlers in sorted order.
        :rtype: list[TaskHandler]
        """
        if cached := self._resolution_cache.get((caller_cls, domain)):
            return cached

        handlers = self.handler_registry.find(caller_cls=caller_cls, domain=domain)

        # Sort by priority maintaining relative ordering within each level
        handlers = sorted(handlers, key=lambda h: (
            h.priority,
            -caller_cls.class_distance(h.caller_cls),
            # -h.domain_specificity(domain),
            # todo: we are just using * fnmatch for now, how are domains represented and dist measured?
            h.registration_order
        ))

        self._resolution_cache[(caller_cls, domain)] = handlers
        return handlers

    def execute(self, entity: EntityT, **context) -> ResultT:
        """
        Execute all applicable handlers for a given entity, combining
        results according to :attr:`pipeline_strategy`.

        :param entity: The entity to be processed by the pipeline.
        :type entity: EntityT
        :param context: Additional keyword arguments to pass to each handler.
        :return: The result of combining handler outputs (may be None,
                 a list, a boolean, etc., depending on the strategy).
        :rtype: ResultT
        :raises ValueError: If no handlers are found for the entity.
        """
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
