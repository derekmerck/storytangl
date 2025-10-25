from typing import List, Callable, Any, Literal, Optional, Type, TYPE_CHECKING, Iterable
from collections import ChainMap
import logging

from tangl.type_hints import UniqueLabel
from .strategy_registry import StrategyRegistry
from .priority_enum import Priority

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

ResultMode = Literal['first', 'merge', 'flatten', 'all_true', 'iter', 'pipeline', 'chain']

class BaseHandler:
    """
    BaseHandler provides a "contextual dispatch" system.  It resolves and
    executes an ordered list of functions for a task and calling class based on:

    - Behavioral grouping ("task" handlers)
    - Class hierarchy (MRO)
    - External categorization ("domain" plugins)

    It can also finalize the result in several different ways, from returning
    the entire list of results, an iterator of method calls, to flattening to a
    single primitive type.

    Functions can be registered directly or using a decorator.
    """
    @classmethod
    def strategy(cls, task_id: UniqueLabel,
                 domain: UniqueLabel = "global",
                 priority: int = Priority.NORMAL ):

        def decorator(func):
            cls.register_strategy(func, task_id, domain, priority)
            return func

        return decorator

    @classmethod
    def register_strategy(cls,
                          func: Callable,
                          task_id: UniqueLabel,
                          domain: UniqueLabel = "global",
                          priority: int = Priority.NORMAL):
        StrategyRegistry(label=domain).register_strategy(func, task_id, priority)

    @classmethod
    def deregister_strategy(cls, task_id: UniqueLabel, *strategies: Callable):
        for strategy in strategies:
            StrategyRegistry.deregister_strategy(task_id, strategy)

    @classmethod
    def _gather_strategies(cls,
                           task_id: UniqueLabel,
                           domains: Iterable[UniqueLabel] = None,
                           caller_cls: Type = None) -> list[Callable]:
        domains = set(domains) if domains else set()
        domains.add("global")
        strategies = []
        for domain in domains:
            if not domain:
                logger.warning("Found null domain?")
                continue

            if StrategyRegistry.has_instance(domain):
                registry = StrategyRegistry.get_instance(domain)
                strategies_ = registry.get_strategies(task_id, caller_cls)
                strategies.extend(strategies_)

        # sort all strategies in priority order, high priority = 0
        strategies = sorted(strategies, key=lambda x: getattr(x, 'strategy_priority', Priority.NORMAL))
        return strategies

    @classmethod
    def execute_task(cls, caller, task_id: str,
                     domains: Iterable[UniqueLabel] = None,
                     result_mode: Optional[ResultMode] = None,
                     **kwargs):
        if isinstance(caller, Type):
            caller_cls = caller
        else:
            caller_cls = type(caller)

        domains = set(domains) if domains else set()
        if hasattr(caller, "domain") and getattr(caller, "domain"):
            domains.add( getattr(caller, "domain") )

        all_strategies = cls._gather_strategies(task_id, domains, caller_cls)

        return cls.execute_strategies(all_strategies, caller, result_mode=result_mode, **kwargs)

    @staticmethod
    def execute_strategies(strategies: List[Callable], caller: Any,
                           result_mode: Optional[ResultMode] = None,
                           **kwargs) -> Any:

        logger.debug("Executing strategies")

        if result_mode == "iter":
            return ( s(caller, **kwargs) for s in strategies )

        results = []
        for strategy in strategies:
            logger.debug(f"Executing strategy <{strategy.__name__}:p={strategy.strategy_priority}>")
            result = strategy(caller, **kwargs)
            if result is not None:
                if result_mode == "first":
                    logger.debug(f"Returning first {result!r}")
                    return result
                if result_mode == "all_true" and not result:
                    # early exit on fail
                    logger.debug(f"failing on strategy <{strategy.__name__}>")
                    return False
                results.append(result)
                if result_mode == "pipeline":
                    # feed result into the next loop
                    if result:
                        caller, kwargs = result
                    logger.debug( [caller, kwargs] )

        logger.debug("Finished executing strategies")

        match result_mode:
            case "first":
                # avoided returning anything
                return None
            case "all_true":
                # avoided early exit
                logger.debug(f"All strategies succeeded")
                return True
            case "merge" | "chain":
                # logger.debug("Merging or chaining result")
                if not all(isinstance(r, dict) for r in results):
                    raise RuntimeError("Cannot merge non-dict results")
                chained_result = ChainMap(*reversed(results))
                if result_mode == "chain":
                    return chained_result
                # logger.debug("Merging chained result")
                return dict(chained_result)
            case "flatten":
                if not all(isinstance(r, list) for r in results):
                    raise RuntimeError("Cannot flatten non-list results")
                return [item for sublist in results for item in sublist]
            case "pipeline":
                # just want the final result
                if results:
                    return results[-1]
                else:
                    return caller, kwargs  # No update

        return results
