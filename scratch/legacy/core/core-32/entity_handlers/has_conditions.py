from __future__ import annotations
from typing import Any, Optional, Self
import logging
from random import random

from tangl.type_hints import Expr, StringMap
from tangl.utils.safe_builtins import safe_builtins
# from ..graph import Node
from ..handler_pipeline import HandlerPipeline, PipelineStrategy
from .has_context import HasContext

logger = logging.getLogger(__name__)

# todo: separate on_gather_exprs, on_runtime_exprs?  Is the gathering the pluggable part?

on_check_conditions = HandlerPipeline[HasContext, bool](
    label="on_check_conditions",
    pipeline_strategy=PipelineStrategy.ALL)
"""
The global pipeline for testing conditions on an Entity. Handlers for 
testing conditions should decorate methods with ``@on_check_conditions.register(...)``.
"""

class HasConditions(HasContext):

    conditions: list[Expr] = None

    @classmethod
    def eval_expr(cls, s: Expr, **context) -> Any:
        if not s:
            return
        result = eval(s, {'random': random, '__builtins__': safe_builtins}, context)
        logger.debug(f"eval {s} with {context} = {result}")
        return result

    @classmethod
    def all_conditions_true(cls, conditions: list[Expr], **context) -> bool:
        return all([ cls.eval_expr( c, **context ) for c in conditions ])

    @on_check_conditions.register()
    def _check_my_conditions(self, **context) -> bool:
        logger.debug(f"check_my_conditions {context}")
        return self.all_conditions_true(self.conditions, **context)

    # @on_check_conditions.register(caller_cls=Node)
    # def _check_my_parent_conditions(self, **context) -> Optional[bool]:
    #     # todo: it's unclear whether we want to inherit conditions by default...
    #     if self.parent and isinstance(self.parent, HasConditions):
    #         return on_check_conditions.execute(self.parent, **context)

    def check_conditions(self, **context) -> bool:
        context = context or self.gather_context()
        return on_check_conditions.execute(self, **context)

    def check_satisfied_by(self, entity: Self) -> bool:
        context = entity.gather_context()
        return on_check_conditions.execute(self, **context)
