import functools

from typing import List, Callable, Any, Literal, Optional, Type, Iterable, Mapping
from collections import ChainMap
import inspect

from .domain_strategy_manager import DomainStrategyManager

ResultMode = Literal['first', 'merge', 'flatten', 'all_true', 'iter']


class StrategyHandler:

    @classmethod
    def strategy(cls, task_id: str, priority: int = 50):

        def decorator(func):
            setattr(func, "strategy_task_id", task_id)
            setattr(func, "strategy_priority", priority)
            return func

        return decorator

    @classmethod
    def register_domain_strategy(cls, domain: str, task_id: str, strategy: Callable, priority: int = 50):
        DomainStrategyManager.get(domain).register_strategy(task_id, strategy, priority)

    @functools.lru_cache
    @staticmethod
    def _collect_strategies(entity_cls: Type, strategy_task: str) -> List[Callable]:
        strategies = []
        for cls in entity_cls.__mro__:
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if getattr(method, "strategy_task_id", False) == strategy_task:
                    strategies.append(method)
        return sorted(strategies, key=lambda x: getattr(x, 'strategy_priority', 50))

    @functools.lru_cache
    @staticmethod
    def _gather_strategies(entity_cls, domain, task_id) -> list[Callable]:
        # strategies can come from the MRO or from a node's domain, domain strategies
        mro_strategies = StrategyHandler._collect_strategies(entity_cls, task_id)

        domain_strategies = DomainStrategyManager.get(domain).get_strategies(task_id)

        # sort them in priority order
        all_strategies = sorted(mro_strategies + domain_strategies,
                                key=lambda x: getattr(x, 'strategy_priority', 50))
        return all_strategies

    @classmethod
    def execute_task(cls, entity: Any, task_id: str, *args,
                     result_mode: Optional[ResultMode] = None,
                     **kwargs):
        entity_cls = type(entity)

        all_strategies = StrategyHandler._gather_strategies(entity_cls, entity.domain, task_id)

        return cls.execute_strategies(all_strategies, entity, *args,
                                      result_mode=result_mode, **kwargs)

    @staticmethod
    def execute_strategies(strategies: List[Callable], entity: Any, *args,
                           result_mode: Optional[ResultMode] = None,
                           **kwargs) -> Any:
        # The return type is typically in Iterable | Mapping | list | bool | NodeType,
        # however, 'first_result' can return anything, so it's safer to user Any.

        if result_mode == "iter":
            return ( s(entity, *args, **kwargs) for s in strategies )

        results = []
        for strategy in strategies:
            result = strategy(entity, *args, **kwargs)
            if result is not None:
                if result_mode == "first":
                    return result
                if result_mode == "all_true" and not result:
                    # early exit on fail
                    return False
                results.append(result)

        if result_mode == "all_true":
            # avoided early exit
            return True
        elif result_mode == "merge":
            if all(isinstance(r, dict) for r in results):
                return ChainMap(*reversed(results))
                # is there a reason to flatten this into a dict before returning?
                # return dict(ChainMap(*reversed(results)))
            raise RuntimeError("Cannot merge non-dict results")
        elif result_mode == "flatten":
            if all(isinstance(r, list) for r in results):
                return [item for sublist in results for item in sublist]
            raise RuntimeError("Cannot flatten non-list results")

        return results
