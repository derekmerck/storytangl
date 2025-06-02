from __future__ import annotations
from typing import Mapping
import random
import logging

from pydantic import BaseModel, Field

from tangl.type_hints import Strings
from tangl.utils.safe_builtins import safe_builtins
from ..base_handler import BaseEntityHandler
from .namespace import HasNamespace
from .available import AvailabilityHandler

logger = logging.getLogger("tangl.condition")
logger.setLevel(logging.WARNING)


class ConditionHandler(BaseEntityHandler):
    """
    A handler class for managing and evaluating conditional strategies in Entity classes.
    Provides functionality to check conditions using dynamic namespaces.

    KeyFeatures:
      - `check_conditions(entity)`: Evaluates conditions attached to entity
      - `check_conditions_satisfied_by(conditions, entity)`: Evaluates conditions give a reference entity
    """

    default_strategy_annotation = "is_condition_strategy"

    @classmethod
    def check_expr(cls, condition: str, ns: Mapping = None):
        """
        Evaluate a expression string within the given namespace.

        :param condition: The condition string to be evaluated.
        :param ns: A mapping of variables to be used in the condition.
        :return: The result of the condition evaluation.
        """
        try:
            ns = {**ns} or {}
            return eval( condition, {'random': random, '__builtins__': safe_builtins}, ns )
        except (SyntaxError, TypeError, KeyError, AttributeError, NameError) as e:
            logger.error(f"Failed to evaluate '{condition}': {e}")
            raise

    @classmethod
    def check_conditions_satisfied_by(cls, conditions: Strings, entity: HasNamespace) -> bool:
        if not conditions:
            return True
        ns = entity.get_namespace()
        return all([cls.check_expr(s, ns) for s in conditions])

    @classmethod
    def check_conditions(cls, entity: HasNamespace) -> bool:
        conditions = cls.invoke_strategies(entity, result_handler="flatten")  # type: Strings
        return cls.check_conditions_satisfied_by(conditions, entity)


class Conditional(HasNamespace):
    """
    A mixin class that adds conditional logic to Entity classes.
    It provides strategies to check conditions and determine entity availability.

    Key Features:
      - `conditions`: A list of conditions that determine if certain actions or effects can be applied.
      - `check_conditions()`: Method that interfaces with `ConditionHandler` to evaluate conditions.
      - `check_satisfied_by(entity)`: Method that interfaces with `ConditionHandler` to evaluate another entity with respect to this entity's conditions.
    """

    conditions: Strings = Field(default_factory=list)

    @ConditionHandler.strategy
    def _get_conditions(self):
        return self.conditions

    @AvailabilityHandler.strategy
    def _conditions_satisfied(self) -> bool:
        return ConditionHandler.check_conditions(self)

    def check_conditions(self) -> bool:
        """
        Check if all conditions for the entity are met.

        :return: True if conditions are met, False otherwise.
        """
        return ConditionHandler.check_conditions(self)

    def check_satisfied_by(self, entity):
        """
        Check if all conditions for this Entity are met by a different Entity.

        :return: True if conditions are met, False otherwise.
        """
        return ConditionHandler.check_conditions_satisfied_by(self.conditions, entity)
