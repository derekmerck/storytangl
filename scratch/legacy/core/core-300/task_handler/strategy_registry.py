from typing import Callable, Type, ClassVar
import logging

from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.utils.is_method_in_mro import is_method_in_mro
from tangl.core.singleton import LabelSingleton
from .priority_enum import Priority

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class StrategyRegistry(LabelSingleton):

    # task_signatures: ClassVar[dict[UniqueLabel, Callable]] = dict()

    strategies: dict[UniqueLabel, list[Callable]] = Field(default_factory=dict)

    # def __init__(self, **kwargs):
    #     self.strategies: dict[UniqueLabel, list[Callable]] = dict()
    #     super().__init__(**kwargs)

    def keys(self):
        return list(self.strategies.keys())

    # @classmethod
    # def register_task_signature(cls, task_id: str, strategy: Callable):
    #     cls.task_signatures[task_id] = strategy

    @classmethod
    def deregister_strategy(cls, task_id: str, strategy: Callable):
        for registry in cls._instances.values():
            registry: StrategyRegistry
            if strategies := registry.strategies.get(task_id):
                logger.debug( strategies )
                if strategy in strategies:
                    strategies.remove(strategy)

    def register_strategy(self,
                          strategy: Callable,
                          task_id: str,
                          priority: int = Priority.NORMAL):
        if task_id not in self.strategies:
            self.strategies[task_id] = []
        if strategy in self.strategies[task_id]:
            return
        logger.debug(f"Registering strategy {strategy}")
        setattr(strategy, 'strategy_task_id', task_id)
        setattr(strategy, 'strategy_priority', priority)
        self.strategies[task_id].append(strategy)
        self.strategies[task_id].sort(key=lambda x: getattr(x, 'strategy_priority', Priority.NORMAL))

    def get_strategies(self, task_id: str, caller_cls: Type = None) -> list[Callable]:
        strategies = self.strategies.get(task_id, [])
        # Registered staticmethods, classmethods, and lambdas are considered to be
        # globally applicable to their task/domain, however, instance methods must be
        # in the mro of the calling class.
        if caller_cls is not None:
            strategies = filter(lambda x: isinstance(x, (classmethod, staticmethod)) or
                                          x.__name__ == "<lambda>" or
                                          is_method_in_mro(x, caller_cls),
                                strategies)
            strategies = list(strategies)

            # if spec_strategy := self.task_signatures.get(task_id):
            #     for strategy in strategies:
            #         if not compare_ftypes(spec_strategy, strategy):
            #             raise ValueError(f'Strategy {strategy.__name__} task signature does not match.')

        return strategies
