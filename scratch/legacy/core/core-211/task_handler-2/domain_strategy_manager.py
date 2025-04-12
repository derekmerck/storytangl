from typing import Dict, List, Callable

class Singleton:

    _instances = dict()
    @classmethod
    def get(cls, label):
        if label not in cls._instances:
            cls._instances[label] = cls()
        return cls._instances[label]

    @classmethod
    def discard_instance(cls, label):
        if label in cls._instances:
            del cls._instances[label]


class StrategyRegistry:

    def __init__(self):
        self.strategies: Dict[str, List[Callable]] = {}

    def register_strategy(self, task_id: str, strategy: Callable, priority: int = 50):
        if task_id not in self.strategies:
            self.strategies[task_id] = []
        setattr(strategy, 'strategy_task_id', task_id)
        setattr(strategy, 'strategy_priority', priority)
        self.strategies[task_id].append(strategy)
        self.strategies[task_id].sort(key=lambda x: getattr(x, 'strategy_priority', 50))

    def get_strategies(self, task_id: str) -> List[Callable]:
        return self.strategies.get(task_id, [])


class DomainStrategyManager(StrategyRegistry, Singleton):

    @classmethod
    def strategy(cls, domain: str, task_id: str, priority: int = 50):
        def decorator(func):
            nonlocal domain
            domain = DomainStrategyManager.get(domain)
            domain.register_strategy(task_id, func, priority)
            return func

        return decorator

