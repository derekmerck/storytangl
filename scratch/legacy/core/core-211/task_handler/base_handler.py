from __future__ import annotations
from typing import Callable, Optional, Literal, ClassVar, TYPE_CHECKING, Type, Self
from collections import ChainMap
import functools
import logging

from tangl.utils.flatten_list import flatten
from tangl.utils.inheritance_aware import InheritanceAware

if TYPE_CHECKING:
    from .entity import EntityType

logger = logging.getLogger("tangl.handler")
logger.setLevel(logging.WARNING)

class BaseEntityHandler(InheritanceAware):
    """
    A base handler providing utilities to manage strategies for entity behaviors.

    Key Features:
      - `strategy()`: A decorator to mark methods as strategies with priorities, which can alter the order in which strategies are evaluated.
      - `invoke_strategies()`: Executes strategies for an entity or class, allowing for flexible behavior customization.
    """

    default_strategy_annotation: ClassVar[str] = "handler_strategy"

    @classmethod
    def strategy(cls, func: Callable, strategy_annotation: str = None, priority: int = 50):
        """
        Decorator to mark a method as a _strategy_ for this handler.  If no strategy
        annotation string is provided, the default annotation string for the handler
        class is used.

        Priority ranges from 0 to 100.  Lowest is run first. Paradoxically, 0 is the
        _lowest_ priority for merged results, because its contribution could be overwritten
        by any other strategy's results.  Default priority is 50.
        """
        strategy_annotation = strategy_annotation or cls.default_strategy_annotation
        setattr(func, strategy_annotation, True)
        setattr(func, "strategy_priority", priority)
        return func

    @staticmethod
    @functools.lru_cache
    def gather_strategies(cls: Type[EntityType], strategy_annotation: str) -> list[Callable]:
        # Cached as it is essentially static after classes are created

        ignore_fields = ["__fields__"]   # deprecated

        strategies = [getattr(cls, attr) for attr in dir(cls) if
                      attr not in ignore_fields and
                      getattr(getattr(cls, attr, None), strategy_annotation, False)]
        return sorted(strategies, key=lambda x: getattr(x, 'strategy_priority', 50))

    @classmethod
    def invoke_strategies(cls,
                          entity: EntityType,
                          *args,
                          entity_cls: Type[EntityType] = None,
                          strategy_annotation: str = None,
                          result_handler: Optional[Literal['first', 'merge', 'flatten']] = None,
                          **kwargs):

        if not entity_cls and not entity:
            raise ValueError("Must have at least one of `entity` or `entity_cls`")
        entity_cls = entity_cls or entity.__class__
        # logger.debug(f"Using {entity_cls} as entity_cls")
        strategy_annotation = strategy_annotation or cls.default_strategy_annotation
        strategies = cls.gather_strategies(entity_cls, strategy_annotation)
        logger.debug( f"strategies: {strategies}" )
        res = []
        for func in strategies:
            if entity:
                res_ = func(entity, *args, **kwargs)
            else:
                res_ = func(entity_cls, *args, **kwargs)
            if res_ is not None:
                if result_handler == "first":
                    return res_
                res.append(res_)
        if result_handler == "merge":
            if all([isinstance(r, dict) for r in res]):
                return {**ChainMap(*reversed(res))}
            else:
                raise RuntimeError(f"Cannot merge result {res}")
        elif result_handler == "flatten":
            if all([isinstance(r, list) for r in res]):
                return flatten(res)
            else:
                raise RuntimeError(f"Cannot flatten result {res}")
        return res

    @classmethod
    def get_subclass_by_name(cls, cls_name: str) -> Self:
        """
        Get a subclass by its name, searching recursively through all subclasses.
        """
        subclasses_by_name_map = {subclass.__name__: subclass for subclass in cls.get_all_subclasses()}
        return subclasses_by_name_map[cls_name]