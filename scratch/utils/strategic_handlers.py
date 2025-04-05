from __future__ import annotations
from typing import Callable,  ClassVar
import logging

logger = logging.getLogger("tangl.strategy")
logger.setLevel(logging.WARNING)

class PipelineStrategyHandler:
    # todo: refactor BaseEntityHandler to abstract the tagged pipeline logic
    pass

# --------------

class StrategyRegistry:
    """
    A registry for opponent move selection strategies.
    Strategies are functions that take the game state and optionally the last player move,
    and return the move for the opponent.
    """

    def __init__(self):
        self._strategies = {}

    def register_strategy(self, name: str, strategy: Callable):
        """
        Register a new strategy with a given name.

        :param name: The name of the strategy.
        :param strategy: The strategy function to register.
        """
        if name in self._strategies:
            raise ValueError(f"Strategy {name} is already registered.")
        self._strategies[name] = strategy

    def get_strategy(self, name: str) -> Callable:
        """
        Retrieve a strategy by its name.

        :param name: The name of the strategy to retrieve.
        :return: The strategy function.
        """
        strategy = self._strategies.get(name)
        if not strategy:
            for k, v in self._strategies.items():
                if k.endswith(f".{name}"):
                    return v
            raise KeyError(f"Strategy {name} not found.")
        return strategy

    def __contains__(self, item):
        value = self.get_strategy(item)
        if value:
            return True
        return False

    def list_strategies(self, annotation: str = None) -> list:
        """
        List all registered strategies.

        :return: A list of registered strategy names.
        """
        if annotation:
            return [ k.split(".") for k in self._strategies.keys() if k.startswith(annotation) ]
        return list(self._strategies.keys())

class NamedStrategyHandler:

    strategy_registry: ClassVar[StrategyRegistry] = StrategyRegistry()

    @classmethod
    def register_strategy(cls, name: str, func: Callable):
        cls.strategy_registry.register_strategy(name, func)

    @classmethod
    def get_strategy(cls, name: str) -> Callable:
        return cls.strategy_registry.get_strategy(name)

    @staticmethod
    def annotate_strategy(name, func):
        logger.debug(f'annotating {name} on {func.__name__}')
        func.strategy_annotation = name
        return func

    def __init_subclass__(cls, **kwargs):
        cls.strategy_registry = StrategyRegistry()
        logger.debug(f'init subclass {cls}')

        ignore_fields = ["__fields__", "__abstractmethods__"]   # deprecated

        # logger.debug( dir(cls) )

        strategies = [getattr(cls, attr_name) for attr_name in dir(cls) if
                      attr_name not in ignore_fields and
                      hasattr(getattr(cls, attr_name), 'strategy_annotation')]

        logger.debug(f"found strategies: {strategies}")

        for s in strategies:
            name = f"{s.strategy_annotation}.{s.__name__}"
            cls.strategy_registry.register_strategy(name, s)

        super().__init_subclass__(**kwargs)
