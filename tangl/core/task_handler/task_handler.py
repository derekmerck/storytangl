from __future__ import annotations
from typing import Callable, Any, Type, Optional, Union
from enum import IntEnum
import inspect
import logging

from pydantic import Field

from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.core.entity import Entity, Registry, Singleton

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
    registration_order: Optional[int] = -1
    # unregistered handlers will sort after registered handlers within a
    # priority by the order they are passed in.

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
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
                    # raise ValueError("Cannot get outer scope name for module-level func")
                    return None
                possible_class_name = parts[-2]  # the thing before .method_name
                logger.debug(f'Parsing {possible_class_name}')
                try:
                    self.caller_cls_ = dereference_obj_cls(Entity, possible_class_name)
                except ValueError:
                    # return None if we can't evaluate it
                    pass
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

    def has_func_name(self, name: str) -> bool:
        return self.func.__name__ == name

    def has_caller_cls(self, caller_cls: Type[Entity]) -> bool:
        """
        Determine if this handler can apply to the given ``caller_cls``
        based on class hierarchy.

        - If ``self.func`` is a classmethod, staticmethod, or lambda,
          it's considered globally applicable.
        - Otherwise, we check that the given ``caller_cls`` is a
          subclass of the declared or inferred ``self.caller_cls``.

        :param caller_cls: The class of the entity being processed.
        :type caller_cls: Type[EntityT]
        :return: True if it should apply, False otherwise.
        :rtype: bool
        :raises ValueError: If we cannot evaluate or infer the
                            handler's ``caller_cls``.
        """
        if self.caller_cls is None:  # accepts unbounded
            return True
        elif self.caller_cls:
            # logger.debug(f"subclass check child {caller_cls.__name__} is sub of parent {self.caller_cls.__name__}: {issubclass(caller_cls, self.caller_cls)}")
            return issubclass(caller_cls, self.caller_cls)
        elif isinstance(self.func, (classmethod, staticmethod)) or self.func.__name__ == "<lambda>":
            return True
        raise ValueError(f"Cannot evaluate {self.func.__qualname__} caller_cls {self.caller_cls} of type {type(self.caller_cls)}")


