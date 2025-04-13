from __future__ import annotations
from typing import TypeVar, Callable, Iterable
import logging

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.core import Entity, Registry
from .task_handler import TaskHandler, HandlerPriority

# Type variables
EntityT = TypeVar('EntityT', bound=Entity)
ResultT = TypeVar('ResultT')

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class HandlerRegistry(Entity):

    handler_registry: Registry[TaskHandler] = Field(default_factory=Registry[TaskHandler])
    handler_registrations: int = 0  # can't just use len, b/c we allow unregistering handlers

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
          >>> strategy_registry = TaskHandlerRegistry()
          >>> @strategy_registry.register(priority=HandlerPriority.FIRST)
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

    def _register_handler(self, handler: TaskHandler):
        """
        Internal helper to place a handler in the registry, and
        increment the registration count.
        """
        handler.registration_order = self.handler_registrations
        self.handler_registrations += 1
        self.handler_registry.add(handler)

    def _unregister_handler(self, handler: TaskHandler):
        """
        Remove a handler from the registry.
        """
        self.handler_registry.remove(handler)
        # but don't decrement the registration counter

    def execute(self, entity: EntityT, func_name: Identifier, **context) -> ResultT:
        """
        Execute a single registered handler for a given entity within a context.

        This allows the task handler registry to be used as a 'strategy registry'.
        """
        task_handler = self.handler_registry.find_one(func_name=func_name)
        if task_handler is None:
            raise RuntimeError(f"No handler registered on {self.label} for {func_name}")

        logger.debug(f"{self.label} pipeline handler to invoke: {task_handler.func.__name__}")

        if not task_handler:
            raise ValueError(f"No handler found for {self.label} with func_name {func_name}")

        return task_handler.func(entity, **context)

    def func_names(self) -> Iterable[str]:
        return [ v.func.__name__ for v in self.handler_registry.values() ]